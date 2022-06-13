#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################

import warnings
from typing import Optional

import torch
import torch.nn as nn
from torch.nn.modules.loss import _Loss
import torch.nn.functional as F

def to_one_hot(labels: torch.Tensor, num_classes: int, dtype: torch.dtype = torch.float, dim: int = 1) -> torch.Tensor:
    # if `dim` is bigger, add singleton dim at the end
    if labels.ndim < dim + 1:
        shape = list(labels.shape) + [1] * (dim + 1 - len(labels.shape))
        labels = torch.reshape(labels, shape)

    sh = list(labels.shape)

    if sh[dim] != 1:
        raise AssertionError("labels should have a channel with length equal to one.")

    sh[dim] = num_classes

    o = torch.zeros(size=sh, dtype=dtype, device=labels.device)
    labels = o.scatter_(dim=dim, index=labels.long(), value=1)

    return labels

# L_CE_1
class PolyLoss(_Loss):
    def __init__(self,
                 softmax: bool = True,
                 ce_weight: Optional[torch.Tensor] = None,
                 reduction: str = 'mean',
                 epsilon: float = 1.0,
                 ) -> None:
        super().__init__()
        self.softmax = softmax
        self.reduction = reduction
        self.epsilon = epsilon
        self.cross_entropy = nn.CrossEntropyLoss(weight=ce_weight, reduction='none')

    def forward(self, input: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """
        Args:
            input: the shape should be BNH[WD], where N is the number of classes.
                You can pass logits or probabilities as input, if pass logit, must set softmax=True
            target: if target is in one-hot format, its shape should be BNH[WD],
                if it is not one-hot encoded, it should has shape B1H[WD] or BH[WD], where N is the number of classes, 
                It should contain binary values

        Raises:
            ValueError: When ``self.reduction`` is not one of ["mean", "sum", "none"].
       """
        if len(input.shape) - len(target.shape) == 1:
            target = target.unsqueeze(1).long()
        n_pred_ch, n_target_ch = input.shape[1], target.shape[1]
        # target not in one-hot encode format, has shape B1H[WD]
        if n_pred_ch != n_target_ch:
            # squeeze out the channel dimension of size 1 to calculate ce loss
            self.ce_loss = self.cross_entropy(input, torch.squeeze(target, dim=1).long())
            # convert into one-hot format to calculate ce loss
            target = to_one_hot(target, num_classes=n_pred_ch)
        else:
            # # target is in the one-hot format, convert to BH[WD] format to calculate ce loss
            self.ce_loss = self.cross_entropy(input, torch.argmax(target, dim=1))

        if self.softmax:
            if n_pred_ch == 1:
                warnings.warn("single channel prediction, `softmax=True` ignored.")
            else:
                input = torch.softmax(input, 1)

        pt = (input * target).sum(dim=1)  # BH[WD]
        poly_loss = self.ce_loss + self.epsilon * (1 - pt)

        if self.reduction == 'mean':
            polyl = torch.mean(poly_loss)  # the batch and channel average
        elif self.reduction == 'sum':
            polyl = torch.sum(poly_loss)  # sum over the batch and channel dims
        elif self.reduction == 'none':
            # BH[WD] 
            polyl = poly_loss
        else:
            raise ValueError(f'Unsupported reduction: {self.reduction}, available options are ["mean", "sum", "none"].')
        return (polyl)



from typing import Any, List, Optional, Union
from torch import Tensor
def poly_loss(
    x: Tensor,
    target: Tensor,
    eps: float = 2.,
    weight: Optional[Tensor] = None,
    ignore_index: int = -100,
    reduction: str = 'mean',
) -> Tensor:
    """Implements the Poly1 loss from `"PolyLoss: A Polynomial Expansion Perspective of Classification Loss
    Functions" <https://arxiv.org/pdf/2204.12511.pdf>`_.

    Args:
        x (torch.Tensor[N, K, ...]): predicted probability
        target (torch.Tensor[N, K, ...]): target probability
        eps (float, optional): epsilon 1 from the paper
        weight (torch.Tensor[K], optional): manual rescaling of each class
        ignore_index (int, optional): specifies target value that is ignored and do not contribute to gradient
        reduction (str, optional): reduction method

    Returns:
        torch.Tensor: loss reduced with `reduction` method
    """

    # log(P[class]) = log_softmax(score)[class]
    logpt = F.log_softmax(x, dim=1)

    # Compute pt and logpt only for target classes (the remaining will have a 0 coefficient)
    logpt = logpt.transpose(1, 0).flatten(1).gather(0, target.view(1, -1)).squeeze()
    # Ignore index (set loss contribution to 0)
    valid_idxs = torch.ones(target.view(-1).shape[0], dtype=torch.bool, device=x.device)
    if ignore_index >= 0 and ignore_index < x.shape[1]:
        valid_idxs[target.view(-1) == ignore_index] = False

    # Get P(class)
    loss = -1 * logpt + eps * (1 - logpt.exp())

    # Weight
    if weight is not None:
        # Tensor type
        if weight.type() != x.data.type():
            weight = weight.type_as(x.data)
        logpt = weight.gather(0, target.data.view(-1)) * logpt

    # Loss reduction
    if reduction == 'sum':
        loss = loss[valid_idxs].sum()
    elif reduction == 'mean':
        loss = loss[valid_idxs].mean()
    else:
        # if no reduction, reshape tensor like target
        loss = loss.view(*target.shape)

    return loss
class _Lossx(nn.Module):

    def __init__(
        self,
        weight: Optional[Union[float, List[float], Tensor]] = None,
        ignore_index: int = -100,
        reduction: str = 'mean',
    ) -> None:
        super().__init__()
        # Cast class weights if possible
        self.weight: Optional[Tensor]
        if isinstance(weight, (float, int)):
            self.register_buffer('weight', torch.Tensor([weight, 1 - weight]))
        elif isinstance(weight, list):
            self.register_buffer('weight', torch.Tensor(weight))
        elif isinstance(weight, Tensor):
            self.register_buffer('weight', weight)
        else:
            self.weight = None
        self.ignore_index = ignore_index
        # Set the reduction method
        if reduction not in ['none', 'mean', 'sum']:
            raise NotImplementedError("argument reduction received an incorrect input")
        self.reduction = reduction
class PolyLoss_1(_Lossx):

    """Implements the Poly1 loss from `"PolyLoss: A Polynomial Expansion Perspective of Classification Loss
    Functions" <https://arxiv.org/pdf/2204.12511.pdf>`_.

    Args:
        weight (torch.Tensor[K], optional): class weight for loss computation
        eps (float, optional): epsilon 1 from the paper
        ignore_index: int = -100,
        reduction: str = 'mean',
    """

    def __init__(
        self,
        *args: Any,
        eps: float = 2.,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.eps = eps

    def forward(self, x: Tensor, target: Tensor) -> Tensor:
        return poly_loss(x, target, self.eps, self.weight, self.ignore_index, self.reduction)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(eps={self.eps}, reduction='{self.reduction}')"


class Poly1FocalLoss(nn.Module):
    def __init__(self,
                 num_classes: int,
                 epsilon: float = 1.0,
                 alpha: float = 0.25,
                 gamma: float = 2.0,
                 reduction: str = "mean"):
        """
        Create instance of Poly1FocalLoss
        :param num_classes: number of classes
        :param epsilon: poly loss epsilon
        :param alpha: focal loss alpha
        :param gamma: focal loss gamma
        :param reduction: one of none|sum|mean, apply reduction to final loss tensor
        """
        super(Poly1FocalLoss, self).__init__()
        self.num_classes = num_classes
        self.epsilon = epsilon
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction
        return

    def forward(self, logits, labels):
        """
        Forward pass
        :param logits: output of neural netwrok of shape [N, num_classes] or [N, num_classes, ...]
        :param labels: ground truth of shape [N] or [N, ...], NOT one-hot encoded
        :return: poly focal loss
        """
        # focal loss implementation taken from
        # https://github.com/facebookresearch/fvcore/blob/main/fvcore/nn/focal_loss.py
        #print("outputs shape:",logits.size());#([16, 1, 64, 64]
        #print("targets1 shape:",labels.size());
        p = torch.sigmoid(logits)

        # if labels are of shape [N]
        # convert to one-hot tensor of shape [N, num_classes]
        '''
        print('labels.ndim:',labels.ndim);
        if labels.ndim == 1:
            labels = F.one_hot(labels.to(torch.int64), num_classes=self.num_classes)
            print("targets2 shape:",labels.size())
        # if labels are of shape [N, ...] e.g. segmentation task
        # convert to one-hot tensor of shape [N, num_classes, ...]
        else:
            labels = F.one_hot(labels.unsqueeze(1).to(torch.int64), self.num_classes).transpose(1, -1).squeeze_(-1)
        print("targets2 shape:",labels.size())
        '''
        labels = labels.to(device=logits.device,
                           dtype=logits.dtype)
        #print("outputs shape:",logits.size());
        #print("targets2 shape:",labels.size());
        ce_loss = F.binary_cross_entropy(logits, labels, reduce=False)
        
        #ce_loss = F.binary_cross_entropy(logits, labels, reduce=False)
        pt = labels * p + (1 - labels) * (1 - p)
        FL = ce_loss * ((1 - pt) ** self.gamma)

        if self.alpha >= 0:
            alpha_t = self.alpha * labels + (1 - self.alpha) * (1 - labels)
            FL = alpha_t * FL

        poly1 = FL + self.epsilon * torch.pow(1 - pt, self.gamma + 1)

        if self.reduction == "mean":
            poly1 = poly1.mean()
        elif self.reduction == "sum":
            poly1 = poly1.sum()
        #poly1.shape torch.Size([16, 1, 64, 64])
        return poly1
class Poly1CrossEntropyLoss(nn.Module):
    def __init__(self,
                 num_classes: int,
                 epsilon: float = 1.0,
                 reduction: str = "mean"):
        """
        Create instance of Poly1CrossEntropyLoss
        :param num_classes:
        :param epsilon:
        :param reduction: one of none|sum|mean, apply reduction to final loss tensor
        """
        super(Poly1CrossEntropyLoss, self).__init__()
        self.num_classes = num_classes
        self.epsilon = epsilon
        self.reduction = reduction
        return

    def forward(self, logits, labels):
        """
        Forward pass
        :param logits: tensor of shape [N, num_classes]
        :param labels: tensor of shape [N]
        :return: poly cross-entropy loss
        """
        #labels_onehot = F.one_hot(labels, num_classes=self.num_classes).to(device=logits.device,
        #                                                                   dtype=logits.dtype)
        pt = torch.sum(labels * F.softmax(logits, dim=-1), dim=-1)
        CE = F.cross_entropy(input=logits, target=labels, reduction='none')
        poly1 = CE + self.epsilon * (1 - pt)
        if self.reduction == "mean":
            poly1 = poly1.mean()
        elif self.reduction == "sum":
            poly1 = poly1.sum()
        return poly1
