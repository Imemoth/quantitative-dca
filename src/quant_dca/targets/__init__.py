"""Future labels only; never import this package from feature producers."""

from quant_dca.targets.builder import ActionCoverage, HorizonTarget, TargetRow, build_targets

__all__ = ['ActionCoverage', 'HorizonTarget', 'TargetRow', 'build_targets']
