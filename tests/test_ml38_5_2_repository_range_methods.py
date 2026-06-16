from app.db.repositories.feature_repository import FeatureRepository
from app.db.repositories.label_repository import LabelRepository


def test_feature_repository_exposes_get_range_inside_class() -> None:
    assert hasattr(FeatureRepository, "get_range")
    assert callable(FeatureRepository.get_range)


def test_label_repository_exposes_get_range_inside_class() -> None:
    assert hasattr(LabelRepository, "get_range")
    assert callable(LabelRepository.get_range)
