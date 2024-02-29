import torch
from torch import nn
import internal.utils.gaussian_utils as gaussian_utils
from internal.utils.general_utils import inverse_sigmoid


class GaussianModelSimplified(nn.Module):
    def __init__(
            self,
            xyz: torch.Tensor,
            features_dc: torch.Tensor,
            features_rest: torch.Tensor,
            scaling: torch.Tensor,
            rotation: torch.Tensor,
            opacity: torch.Tensor,
            filter_3D: torch.Tensor,
            sh_degree: int,
            device,
    ) -> None:
        super().__init__()

        self._xyz = xyz.to(device)
        # self._features_dc = features_dc
        # self._features_rest = features_rest
        self._scaling = torch.exp(scaling).to(device)
        self._rotation = torch.nn.functional.normalize(rotation).to(device)
        self._opacity = torch.sigmoid(opacity).to(device)

        self._features = torch.cat([features_dc, features_rest], dim=1).to(device)

        self._opacity_origin = None

        self.filter_3D = filter_3D.to(device)

        self.max_sh_degree = sh_degree
        self.active_sh_degree = sh_degree

    def to_device(self, device):
        self._xyz = self._xyz.to(device)
        self._scaling = self._scaling.to(device)
        self._rotation = self._rotation.to(device)
        self._opacity = self._opacity.to(device)
        self._features = self._features.to(device)
        self.filter_3D = self.filter_3D.to(device)
        return self

    @classmethod
    def construct_from_state_dict(cls, state_dict, filter_3D, active_sh_degree, device):
        init_args = {
            "filter_3D": filter_3D,
            "sh_degree": active_sh_degree,
            "device": device,
        }
        for i in state_dict:
            if i.startswith("gaussian_model._") is False:
                continue
            init_args[i[len("gaussian_model._"):]] = state_dict[i]
        return cls(**init_args)

    @classmethod
    def construct_from_ply(cls, ply_path: str, sh_degree, device):
        gaussians = gaussian_utils.Gaussian.load_from_ply(ply_path, sh_degree).to_parameter_structure()
        return cls(
            sh_degree=sh_degree,
            device=device,
            xyz=gaussians.xyz,
            opacity=gaussians.opacities,
            features_dc=gaussians.features_dc,
            features_rest=gaussians.features_extra,
            scaling=gaussians.scales,
            rotation=gaussians.rotations,
        )

    @property
    def get_scaling(self):
        return self._scaling

    @property
    def get_scaling_with_3D_filter(self):
        scales = self.get_scaling

        scales = torch.square(scales) + torch.square(self.filter_3D)
        scales = torch.sqrt(scales)
        return scales

    @property
    def get_rotation(self):
        return self._rotation

    @property
    def get_xyz(self):
        return self._xyz

    @property
    def get_features(self):
        return self._features

    @property
    def get_opacity(self):
        return self._opacity

    @property
    def get_opacity_with_3D_filter(self):
        opacity = self.get_opacity
        # apply 3D filter
        scales = self.get_scaling

        scales_square = torch.square(scales)
        det1 = scales_square.prod(dim=1)

        scales_after_square = scales_square + torch.square(self.filter_3D)
        det2 = scales_after_square.prod(dim=1)
        coef = torch.sqrt(det1 / det2)
        return opacity * coef[..., None]

    def select(self, mask: torch.tensor):
        if self._opacity_origin is None:
            self._opacity_origin = torch.clone(self._opacity)  # make a backup
        else:
            self._opacity = torch.clone(self._opacity_origin)

        self._opacity[mask] = 0.

    def delete_gaussians(self, mask: torch.tensor):
        gaussians_to_be_preserved = torch.bitwise_not(mask).to(self._xyz.device)
        self._xyz = self._xyz[gaussians_to_be_preserved]
        self._scaling = self._scaling[gaussians_to_be_preserved]
        self._rotation = self._rotation[gaussians_to_be_preserved]

        if self._opacity_origin is not None:
            self._opacity = self._opacity_origin
            self._opacity_origin = None
        self._opacity = self._opacity[gaussians_to_be_preserved]

        self._features = self._features[gaussians_to_be_preserved]

    def to_parameter_structure(self) -> gaussian_utils.Gaussian:
        xyz = self._xyz.cpu()
        features_dc = self._features[:, :1, :].cpu()
        features_rest = self._features[:, 1:, :].cpu()
        scaling = torch.log(self._scaling).cpu()
        rotation = self._rotation.cpu()
        opacity = inverse_sigmoid(self._opacity).cpu()

        return gaussian_utils.Gaussian(
            sh_degrees=self.max_sh_degree,
            xyz=xyz,
            opacities=opacity,
            features_dc=features_dc,
            features_extra=features_rest,
            scales=scaling,
            rotations=rotation,
        )

    def to_ply_structure(self) -> gaussian_utils.Gaussian:
        xyz = self._xyz.cpu().numpy()
        features_dc = self._features[:, :1, :].transpose(1, 2).cpu().numpy()
        features_rest = self._features[:, 1:, :].transpose(1, 2).cpu().numpy()
        scaling = torch.log(self._scaling).cpu().numpy()
        rotation = self._rotation.cpu().numpy()
        opacity = inverse_sigmoid(self._opacity).cpu().numpy()

        return gaussian_utils.Gaussian(
            sh_degrees=self.max_sh_degree,
            xyz=xyz,
            opacities=opacity,
            features_dc=features_dc,
            features_extra=features_rest,
            scales=scaling,
            rotations=rotation,
        )
