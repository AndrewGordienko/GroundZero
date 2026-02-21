import torch
import torch.nn as nn
import torch.nn.functional as F

class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        residual = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += residual
        return F.relu(out)

class AlphaNet(nn.Module):
    def __init__(self, num_res_blocks=10, channels=128):
        super().__init__()
        
        self.conv_in = nn.Conv2d(25, channels, kernel_size=3, padding=1)
        self.bn_in = nn.BatchNorm2d(channels)
        
        self.res_blocks = nn.ModuleList([ResidualBlock(channels) for _ in range(num_res_blocks)])
        
        # Policy Head
        self.pol_conv = nn.Conv2d(channels, 32, kernel_size=1)
        self.pol_bn = nn.BatchNorm2d(32)
        self.pol_fc = nn.Linear(32 * 8 * 8, 4096) 
        
        # Value Head: Optimized to prevent 0/100 saturation
        self.val_conv = nn.Conv2d(channels, 1, kernel_size=1)
        self.val_bn = nn.BatchNorm2d(1)
        self.val_fc1 = nn.Linear(1 * 8 * 8, 128)
        self.val_fc2 = nn.Linear(128, 1)

        # CRITICAL: Initialize final layer to zero
        # This forces initial predictions to 0.0 (50% win prob)
        nn.init.zeros_(self.val_fc2.weight)
        nn.init.zeros_(self.val_fc2.bias)

    def forward(self, x):
        x = F.relu(self.bn_in(self.conv_in(x)))
        for block in self.res_blocks:
            x = block(x)
        
        # Policy Head
        p = F.relu(self.pol_bn(self.pol_conv(x)))
        p = p.view(p.size(0), -1)
        p = self.pol_fc(p) 
        
        # Value Head: Removed extra ReLUs and BatchNorms that cause saturation
        v = F.relu(self.val_bn(self.val_conv(x)))
        v = v.view(v.size(0), -1)
        v = F.relu(self.val_fc1(v))
        v = torch.tanh(self.val_fc2(v)) # tanh maps to [-1, 1]
        
        return p, v