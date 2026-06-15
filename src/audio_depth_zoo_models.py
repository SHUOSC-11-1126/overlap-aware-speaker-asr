from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
from torch import nn

from .audio_depth_router_common import ROUTE_LABELS


class ConvBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, pool: bool = True) -> None:
        super().__init__()
        layers: list[nn.Module] = [
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        ]
        if pool:
            layers.append(nn.MaxPool2d(2))
        self.block = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class TinyConvClassifier(nn.Module):
    def __init__(self, in_channels: int, width: int = 24, dropout: float = 0.1) -> None:
        super().__init__()
        self.backbone = nn.Sequential(
            ConvBlock(in_channels, width),
            ConvBlock(width, width * 2),
            ConvBlock(width * 2, width * 4, pool=False),
        )
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(width * 4 * 4 * 4, len(ROUTE_LABELS)),
        )

    def forward(self, x: torch.Tensor, tabular: torch.Tensor | None = None) -> torch.Tensor:
        del tabular
        return self.head(self.backbone(x))


class ResidualBlock(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)
        self.act = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x = self.act(self.bn1(self.conv1(x)))
        x = self.bn2(self.conv2(x))
        return self.act(x + residual)


class TinyResNetClassifier(nn.Module):
    def __init__(self, in_channels: int, width: int = 24) -> None:
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, width, kernel_size=3, padding=1),
            nn.BatchNorm2d(width),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
        )
        self.block1 = ResidualBlock(width)
        self.block2 = ResidualBlock(width)
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(),
            nn.Linear(width * 4 * 4, len(ROUTE_LABELS)),
        )

    def forward(self, x: torch.Tensor, tabular: torch.Tensor | None = None) -> torch.Tensor:
        del tabular
        x = self.stem(x)
        x = self.block1(x)
        x = self.block2(x)
        return self.head(x)


class CRNNClassifier(nn.Module):
    def __init__(self, in_channels: int, width: int = 24, gru_hidden: int = 32) -> None:
        super().__init__()
        self.stem = nn.Sequential(
            ConvBlock(in_channels, width),
            ConvBlock(width, width * 2),
            nn.Conv2d(width * 2, width * 2, kernel_size=3, padding=1),
            nn.BatchNorm2d(width * 2),
            nn.ReLU(inplace=True),
        )
        self.gru = nn.GRU(input_size=width * 2, hidden_size=gru_hidden, batch_first=True, bidirectional=True)
        self.head = nn.Linear(gru_hidden * 2, len(ROUTE_LABELS))

    def forward(self, x: torch.Tensor, tabular: torch.Tensor | None = None) -> torch.Tensor:
        del tabular
        x = self.stem(x)
        x = x.mean(dim=2).transpose(1, 2)
        out, _ = self.gru(x)
        pooled = out.mean(dim=1)
        return self.head(pooled)


class PatchTransformerClassifier(nn.Module):
    def __init__(self, in_channels: int, patch_size: int = 8, embed_dim: int = 48, heads: int = 4) -> None:
        super().__init__()
        self.patch_size = patch_size
        self.embed = nn.Linear(in_channels * patch_size * patch_size, embed_dim)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=heads,
            dim_feedforward=embed_dim * 2,
            dropout=0.1,
            batch_first=True,
            activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=1)
        self.cls = nn.Sequential(nn.LayerNorm(embed_dim), nn.Linear(embed_dim, len(ROUTE_LABELS)))

    def forward(self, x: torch.Tensor, tabular: torch.Tensor | None = None) -> torch.Tensor:
        del tabular
        b, c, h, w = x.shape
        ps = self.patch_size
        pad_h = (ps - h % ps) % ps
        pad_w = (ps - w % ps) % ps
        if pad_h or pad_w:
            x = nn.functional.pad(x, (0, pad_w, 0, pad_h))
        patches = x.unfold(2, ps, ps).unfold(3, ps, ps)
        patches = patches.permute(0, 2, 3, 1, 4, 5).contiguous()
        patches = patches.view(b, -1, c * ps * ps)
        tokens = self.embed(patches)
        encoded = self.encoder(tokens)
        pooled = encoded.mean(dim=1)
        return self.cls(pooled)


class TabularMLP(nn.Module):
    def __init__(self, input_dim: int, hidden: int = 64, dropout: float = 0.1) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden, hidden),
            nn.ReLU(inplace=True),
            nn.Linear(hidden, len(ROUTE_LABELS)),
        )

    def forward(self, x: torch.Tensor, tabular: torch.Tensor | None = None) -> torch.Tensor:
        if tabular is None:
            tabular = x
        return self.net(tabular)


class HybridLateFusionClassifier(nn.Module):
    def __init__(self, in_channels: int, tabular_dim: int, width: int = 24) -> None:
        super().__init__()
        self.audio_backbone = nn.Sequential(
            ConvBlock(in_channels, width),
            ConvBlock(width, width * 2),
            nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(),
        )
        self.audio_proj = nn.Sequential(nn.Linear(width * 2 * 4 * 4, 64), nn.ReLU(inplace=True))
        self.tabular_proj = nn.Sequential(nn.Linear(tabular_dim, 64), nn.ReLU(inplace=True))
        self.head = nn.Sequential(nn.Linear(128, 64), nn.ReLU(inplace=True), nn.Linear(64, len(ROUTE_LABELS)))

    def forward(self, x: torch.Tensor, tabular: torch.Tensor | None = None) -> torch.Tensor:
        if tabular is None:
            raise ValueError("Hybrid model requires tabular features")
        audio_embed = self.audio_proj(self.audio_backbone(x))
        tab_embed = self.tabular_proj(tabular)
        return self.head(torch.cat([audio_embed, tab_embed], dim=1))


def build_model(model_name: str, input_channels: int, tabular_dim: int = 0) -> nn.Module:
    if model_name == "mlp_handcrafted":
        return TabularMLP(tabular_dim)
    if model_name == "cnn_logmel":
        return TinyConvClassifier(input_channels)
    if model_name in {"cnn_depth", "cnn_depth_balanced", "analysis_upper_bound_cnn"}:
        return TinyConvClassifier(input_channels)
    if model_name == "resnet_tiny_depth":
        return TinyResNetClassifier(input_channels)
    if model_name == "crnn_depth":
        return CRNNClassifier(input_channels)
    if model_name == "patch_transformer_depth":
        return PatchTransformerClassifier(input_channels)
    if model_name == "hybrid_late_fusion":
        return HybridLateFusionClassifier(input_channels, tabular_dim)
    raise KeyError(f"Unknown AudioDepth zoo model: {model_name}")

