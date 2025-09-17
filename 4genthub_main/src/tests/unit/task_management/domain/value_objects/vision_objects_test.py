"""Test suite for Vision Objects value objects.

Tests the vision system value objects including:
- VisionHierarchyLevel, ContributionType, MetricType enums
- VisionMetric value object
- VisionObjective value object
- VisionAlignment value object
- VisionInsight value object
- VisionDashboard value object
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from unittest.mock import patch

from fastmcp.task_management.domain.value_objects.vision_objects import (
    VisionHierarchyLevel,
    ContributionType,
    MetricType,
    VisionMetric,
    VisionObjective,
    VisionAlignment,
    VisionInsight,
    VisionDashboard
)


class TestEnums:
    """Test cases for vision system enums."""
    
    def test_vision_hierarchy_level_values(self):
        """Test VisionHierarchyLevel enum values."""
        assert VisionHierarchyLevel.ORGANIZATION == "organization"
        assert VisionHierarchyLevel.DEPARTMENT == "department"
        assert VisionHierarchyLevel.TEAM == "team"
        assert VisionHierarchyLevel.PROJECT == "project"
        assert VisionHierarchyLevel.MILESTONE == "milestone"
    
    def test_contribution_type_values(self):
        """Test ContributionType enum values."""
        assert ContributionType.DIRECT == "direct"
        assert ContributionType.SUPPORTING == "supporting"
        assert ContributionType.ENABLING == "enabling"
        assert ContributionType.EXPLORATORY == "exploratory"
        assert ContributionType.MAINTENANCE == "maintenance"
    
    def test_metric_type_values(self):
        """Test MetricType enum values."""
        assert MetricType.PERCENTAGE == "percentage"
        assert MetricType.COUNT == "count"
        assert MetricType.CURRENCY == "currency"
        assert MetricType.TIME == "time"
        assert MetricType.RATING == "rating"
        assert MetricType.CUSTOM == "custom"


class TestVisionMetric:
    """Test cases for VisionMetric value object."""
    
    def test_create_vision_metric_minimal(self):
        """Test creating vision metric with minimal data."""
        metric = VisionMetric(
            name="Revenue",
            current_value=100000.0,
            target_value=150000.0,
            unit="USD"
        )
        
        assert metric.name == "Revenue"
        assert metric.current_value == 100000.0
        assert metric.target_value == 150000.0
        assert metric.unit == "USD"
        assert metric.metric_type == MetricType.CUSTOM
        assert metric.baseline_value == 0.0
        assert isinstance(metric.last_updated, datetime)
    
    def test_create_vision_metric_full(self):
        """Test creating vision metric with all fields."""
        now = datetime.now(timezone.utc)
        
        metric = VisionMetric(
            name="User Satisfaction",
            current_value=4.2,
            target_value=4.5,
            unit="stars",
            metric_type=MetricType.RATING,
            baseline_value=3.0,
            last_updated=now
        )
        
        assert metric.metric_type == MetricType.RATING
        assert metric.baseline_value == 3.0
        assert metric.last_updated == now
    
    def test_vision_metric_immutable(self):
        """Test that vision metric is immutable."""
        metric = VisionMetric(
            name="Test",
            current_value=50.0,
            target_value=100.0,
            unit="units"
        )
        
        with pytest.raises(AttributeError):
            metric.current_value = 75.0
    
    def test_progress_percentage_normal(self):
        """Test progress percentage calculation with normal values."""
        metric = VisionMetric(
            name="Progress",
            current_value=75.0,
            target_value=100.0,
            unit="percent",
            baseline_value=0.0
        )
        
        assert metric.progress_percentage == 75.0
    
    def test_progress_percentage_over_target(self):
        """Test progress percentage when current exceeds target."""
        metric = VisionMetric(
            name="Efficiency",
            current_value=120.0,
            target_value=100.0,
            unit="percent",
            baseline_value=0.0
        )
        
        assert metric.progress_percentage == 100.0
    
    def test_progress_percentage_below_baseline(self):
        """Test progress percentage when current is below baseline."""
        metric = VisionMetric(
            name="Cost",
            current_value=50.0,
            target_value=100.0,
            unit="USD",
            baseline_value=75.0
        )
        
        assert metric.progress_percentage == 0.0
    
    def test_progress_percentage_same_baseline_target(self):
        """Test progress percentage when baseline equals target."""
        metric = VisionMetric(
            name="Maintain",
            current_value=100.0,
            target_value=90.0,
            unit="units",
            baseline_value=90.0
        )
        
        assert metric.progress_percentage == 100.0
        
        # Test when current is below target
        metric2 = VisionMetric(
            name="Maintain2",
            current_value=80.0,
            target_value=90.0,
            unit="units",
            baseline_value=90.0
        )
        
        assert metric2.progress_percentage == 0.0
    
    def test_is_achieved_true(self):
        """Test is_achieved when target is reached."""
        metric = VisionMetric(
            name="Goal",
            current_value=100.0,
            target_value=100.0,
            unit="points"
        )
        
        assert metric.is_achieved
    
    def test_is_achieved_false(self):
        """Test is_achieved when target is not reached."""
        metric = VisionMetric(
            name="Goal",
            current_value=90.0,
            target_value=100.0,
            unit="points"
        )
        
        assert not metric.is_achieved
    
    def test_to_dict(self):
        """Test converting metric to dictionary."""
        now = datetime.now(timezone.utc)
        
        metric = VisionMetric(
            name="Performance",
            current_value=85.0,
            target_value=100.0,
            unit="percent",
            metric_type=MetricType.PERCENTAGE,
            baseline_value=50.0,
            last_updated=now
        )
        
        result = metric.to_dict()
        
        assert result["name"] == "Performance"
        assert result["current_value"] == 85.0
        assert result["target_value"] == 100.0
        assert result["unit"] == "percent"
        assert result["metric_type"] == "percentage"
        assert result["baseline_value"] == 50.0
        assert result["progress_percentage"] == 70.0  # (85-50)/(100-50) * 100
        assert result["is_achieved"] is False
        assert result["last_updated"] == now.isoformat()


class TestVisionObjective:
    """Test cases for VisionObjective value object."""
    
    def test_create_vision_objective_minimal(self):
        """Test creating vision objective with minimal data."""
        objective = VisionObjective()
        
        assert isinstance(objective.id, UUID)
        assert objective.title == ""
        assert objective.description == ""
        assert objective.level == VisionHierarchyLevel.PROJECT
        assert objective.parent_id is None
        assert objective.owner == ""
        assert objective.priority == 1
        assert objective.status == "active"
        assert isinstance(objective.created_at, datetime)
        assert objective.due_date is None
        assert objective.metrics == []
        assert objective.tags == []
        assert objective.metadata == {}
    
    def test_create_vision_objective_full(self):
        """Test creating vision objective with all fields."""
        objective_id = uuid4()
        parent_id = uuid4()
        now = datetime.now(timezone.utc)
        due_date = now + timedelta(days=30)
        
        metrics = [
            VisionMetric(name="Metric1", current_value=50.0, target_value=100.0, unit="units"),
            VisionMetric(name="Metric2", current_value=75.0, target_value=100.0, unit="percent")
        ]
        
        objective = VisionObjective(
            id=objective_id,
            title="Improve User Experience",
            description="Enhance the overall user experience of our application",
            level=VisionHierarchyLevel.DEPARTMENT,
            parent_id=parent_id,
            owner="product_team",
            priority=4,
            status="in_progress",
            created_at=now,
            due_date=due_date,
            metrics=metrics,
            tags=["ux", "quality"],
            metadata={"budget": 50000, "team_size": 5}
        )
        
        assert objective.id == objective_id
        assert objective.title == "Improve User Experience"
        assert objective.description == "Enhance the overall user experience of our application"
        assert objective.level == VisionHierarchyLevel.DEPARTMENT
        assert objective.parent_id == parent_id
        assert objective.owner == "product_team"
        assert objective.priority == 4
        assert objective.status == "in_progress"
        assert objective.created_at == now
        assert objective.due_date == due_date
        assert len(objective.metrics) == 2
        assert objective.tags == ["ux", "quality"]
        assert objective.metadata == {"budget": 50000, "team_size": 5}
    
    def test_vision_objective_immutable(self):
        """Test that vision objective is immutable."""
        objective = VisionObjective(title="Test")
        
        with pytest.raises(AttributeError):
            objective.title = "New Title"
    
    def test_overall_progress_no_metrics(self):
        """Test overall progress calculation with no metrics."""
        objective = VisionObjective()
        
        assert objective.overall_progress == 0.0
    
    def test_overall_progress_with_metrics(self):
        """Test overall progress calculation with metrics."""
        metrics = [
            VisionMetric(name="M1", current_value=50.0, target_value=100.0, unit="units"),  # 50%
            VisionMetric(name="M2", current_value=75.0, target_value=100.0, unit="units"),  # 75%
            VisionMetric(name="M3", current_value=100.0, target_value=100.0, unit="units")  # 100%
        ]
        
        objective = VisionObjective(metrics=metrics)
        
        assert objective.overall_progress == 75.0  # (50 + 75 + 100) / 3
    
    def test_is_completed_no_metrics(self):
        """Test is_completed with no metrics."""
        objective = VisionObjective()
        
        assert not objective.is_completed
    
    def test_is_completed_all_achieved(self):
        """Test is_completed when all metrics are achieved."""
        metrics = [
            VisionMetric(name="M1", current_value=100.0, target_value=100.0, unit="units"),
            VisionMetric(name="M2", current_value=200.0, target_value=100.0, unit="units")
        ]
        
        objective = VisionObjective(metrics=metrics)
        
        assert objective.is_completed
    
    def test_is_completed_not_all_achieved(self):
        """Test is_completed when not all metrics are achieved."""
        metrics = [
            VisionMetric(name="M1", current_value=100.0, target_value=100.0, unit="units"),
            VisionMetric(name="M2", current_value=50.0, target_value=100.0, unit="units")
        ]
        
        objective = VisionObjective(metrics=metrics)
        
        assert not objective.is_completed
    
    def test_days_remaining_no_due_date(self):
        """Test days remaining when no due date is set."""
        objective = VisionObjective()
        
        assert objective.days_remaining is None
    
    def test_days_remaining_future_date(self):
        """Test days remaining with future due date."""
        future_date = datetime.now(timezone.utc) + timedelta(days=10)
        objective = VisionObjective(due_date=future_date)
        
        # Should be around 10, but account for test execution time
        assert 9 <= objective.days_remaining <= 10
    
    def test_days_remaining_past_date(self):
        """Test days remaining with past due date."""
        past_date = datetime.now(timezone.utc) - timedelta(days=5)
        objective = VisionObjective(due_date=past_date)
        
        assert objective.days_remaining == 0
    
    def test_to_dict(self):
        """Test converting objective to dictionary."""
        objective_id = uuid4()
        parent_id = uuid4()
        now = datetime.now(timezone.utc)
        due_date = now + timedelta(days=30)
        
        metrics = [
            VisionMetric(name="Test Metric", current_value=80.0, target_value=100.0, unit="percent")
        ]
        
        objective = VisionObjective(
            id=objective_id,
            title="Test Objective",
            description="Test Description",
            level=VisionHierarchyLevel.TEAM,
            parent_id=parent_id,
            owner="test_owner",
            priority=3,
            status="active",
            created_at=now,
            due_date=due_date,
            metrics=metrics,
            tags=["test", "example"],
            metadata={"key": "value"}
        )
        
        result = objective.to_dict()
        
        assert result["id"] == str(objective_id)
        assert result["title"] == "Test Objective"
        assert result["description"] == "Test Description"
        assert result["level"] == "team"
        assert result["parent_id"] == str(parent_id)
        assert result["owner"] == "test_owner"
        assert result["priority"] == 3
        assert result["status"] == "active"
        assert result["created_at"] == now.isoformat()
        assert result["due_date"] == due_date
        assert len(result["metrics"]) == 1
        assert result["tags"] == ["test", "example"]
        assert result["overall_progress"] == 80.0
        assert result["is_completed"] is False
        assert result["days_remaining"] is not None
        assert result["metadata"] == {"key": "value"}


class TestVisionAlignment:
    """Test cases for VisionAlignment value object."""
    
    def test_create_vision_alignment_minimal(self):
        """Test creating vision alignment with minimal data."""
        task_id = uuid4()
        objective_id = uuid4()
        
        alignment = VisionAlignment(
            task_id=task_id,
            objective_id=objective_id,
            alignment_score=0.8,
            contribution_type=ContributionType.DIRECT
        )
        
        assert alignment.task_id == task_id
        assert alignment.objective_id == objective_id
        assert alignment.alignment_score == 0.8
        assert alignment.contribution_type == ContributionType.DIRECT
        assert alignment.confidence == 0.8
        assert alignment.rationale == ""
        assert isinstance(alignment.calculated_at, datetime)
        assert alignment.factors == {}
    
    def test_create_vision_alignment_full(self):
        """Test creating vision alignment with all fields."""
        task_id = uuid4()
        objective_id = uuid4()
        now = datetime.now(timezone.utc)
        
        alignment = VisionAlignment(
            task_id=task_id,
            objective_id=objective_id,
            alignment_score=0.9,
            contribution_type=ContributionType.SUPPORTING,
            confidence=0.95,
            rationale="Task directly supports objective implementation",
            calculated_at=now,
            factors={"scope_match": 0.9, "skill_alignment": 0.85}
        )
        
        assert alignment.confidence == 0.95
        assert alignment.rationale == "Task directly supports objective implementation"
        assert alignment.calculated_at == now
        assert alignment.factors == {"scope_match": 0.9, "skill_alignment": 0.85}
    
    def test_vision_alignment_immutable(self):
        """Test that vision alignment is immutable."""
        alignment = VisionAlignment(
            task_id=uuid4(),
            objective_id=uuid4(),
            alignment_score=0.5,
            contribution_type=ContributionType.ENABLING
        )
        
        with pytest.raises(AttributeError):
            alignment.alignment_score = 0.9
    
    def test_is_strong_alignment_true(self):
        """Test is_strong_alignment when score is >= 0.7."""
        alignment = VisionAlignment(
            task_id=uuid4(),
            objective_id=uuid4(),
            alignment_score=0.8,
            contribution_type=ContributionType.DIRECT
        )
        
        assert alignment.is_strong_alignment
    
    def test_is_strong_alignment_false(self):
        """Test is_strong_alignment when score is < 0.7."""
        alignment = VisionAlignment(
            task_id=uuid4(),
            objective_id=uuid4(),
            alignment_score=0.6,
            contribution_type=ContributionType.EXPLORATORY
        )
        
        assert not alignment.is_strong_alignment
    
    def test_is_weak_alignment_true(self):
        """Test is_weak_alignment when score is < 0.3."""
        alignment = VisionAlignment(
            task_id=uuid4(),
            objective_id=uuid4(),
            alignment_score=0.2,
            contribution_type=ContributionType.MAINTENANCE
        )
        
        assert alignment.is_weak_alignment
    
    def test_is_weak_alignment_false(self):
        """Test is_weak_alignment when score is >= 0.3."""
        alignment = VisionAlignment(
            task_id=uuid4(),
            objective_id=uuid4(),
            alignment_score=0.4,
            contribution_type=ContributionType.SUPPORTING
        )
        
        assert not alignment.is_weak_alignment
    
    def test_to_dict(self):
        """Test converting alignment to dictionary."""
        task_id = uuid4()
        objective_id = uuid4()
        now = datetime.now(timezone.utc)
        
        alignment = VisionAlignment(
            task_id=task_id,
            objective_id=objective_id,
            alignment_score=0.75,
            contribution_type=ContributionType.DIRECT,
            confidence=0.9,
            rationale="Strong alignment",
            calculated_at=now,
            factors={"relevance": 0.8, "impact": 0.7}
        )
        
        result = alignment.to_dict()
        
        assert result["task_id"] == str(task_id)
        assert result["objective_id"] == str(objective_id)
        assert result["alignment_score"] == 0.75
        assert result["contribution_type"] == "direct"
        assert result["confidence"] == 0.9
        assert result["rationale"] == "Strong alignment"
        assert result["calculated_at"] == now.isoformat()
        assert result["is_strong_alignment"] is True
        assert result["is_weak_alignment"] is False
        assert result["factors"] == {"relevance": 0.8, "impact": 0.7}


class TestVisionInsight:
    """Test cases for VisionInsight value object."""
    
    def test_create_vision_insight_minimal(self):
        """Test creating vision insight with minimal data."""
        insight = VisionInsight()
        
        assert isinstance(insight.id, UUID)
        assert insight.type == "recommendation"
        assert insight.title == ""
        assert insight.description == ""
        assert insight.impact == "medium"
        assert insight.affected_objectives == []
        assert insight.affected_tasks == []
        assert insight.suggested_actions == []
        assert isinstance(insight.created_at, datetime)
        assert insight.expires_at is None
        assert insight.metadata == {}
    
    def test_create_vision_insight_full(self):
        """Test creating vision insight with all fields."""
        insight_id = uuid4()
        objective_id = uuid4()
        task_id = uuid4()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=7)
        
        insight = VisionInsight(
            id=insight_id,
            type="warning",
            title="Resource Shortage",
            description="Team capacity is insufficient for current objectives",
            impact="high",
            affected_objectives=[objective_id],
            affected_tasks=[task_id],
            suggested_actions=["Hire more developers", "Reduce scope"],
            created_at=now,
            expires_at=expires_at,
            metadata={"urgency": "high", "cost": 100000}
        )
        
        assert insight.id == insight_id
        assert insight.type == "warning"
        assert insight.title == "Resource Shortage"
        assert insight.description == "Team capacity is insufficient for current objectives"
        assert insight.impact == "high"
        assert insight.affected_objectives == [objective_id]
        assert insight.affected_tasks == [task_id]
        assert insight.suggested_actions == ["Hire more developers", "Reduce scope"]
        assert insight.created_at == now
        assert insight.expires_at == expires_at
        assert insight.metadata == {"urgency": "high", "cost": 100000}
    
    def test_vision_insight_immutable(self):
        """Test that vision insight is immutable."""
        insight = VisionInsight(title="Test")
        
        with pytest.raises(AttributeError):
            insight.title = "New Title"
    
    def test_is_expired_no_expiry(self):
        """Test is_expired when no expiry date is set."""
        insight = VisionInsight()
        
        assert not insight.is_expired
    
    def test_is_expired_future_expiry(self):
        """Test is_expired with future expiry date."""
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        insight = VisionInsight(expires_at=future_date)
        
        assert not insight.is_expired
    
    def test_is_expired_past_expiry(self):
        """Test is_expired with past expiry date."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        insight = VisionInsight(expires_at=past_date)
        
        assert insight.is_expired
    
    def test_urgency_score_low_impact(self):
        """Test urgency score with low impact."""
        insight = VisionInsight(impact="low")
        
        assert insight.urgency_score == 0.25
    
    def test_urgency_score_medium_impact(self):
        """Test urgency score with medium impact."""
        insight = VisionInsight(impact="medium")
        
        assert insight.urgency_score == 0.5
    
    def test_urgency_score_high_impact(self):
        """Test urgency score with high impact."""
        insight = VisionInsight(impact="high")
        
        assert insight.urgency_score == 0.75
    
    def test_urgency_score_critical_impact(self):
        """Test urgency score with critical impact."""
        insight = VisionInsight(impact="critical")
        
        assert insight.urgency_score == 1.0
    
    def test_urgency_score_expires_tomorrow(self):
        """Test urgency score when expiring within 1 day."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
        insight = VisionInsight(impact="medium", expires_at=expires_at)
        
        # medium (0.5) * 1.5 = 0.75
        assert insight.urgency_score == 0.75
    
    def test_urgency_score_expires_this_week(self):
        """Test urgency score when expiring within 7 days."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=5)
        insight = VisionInsight(impact="medium", expires_at=expires_at)
        
        # medium (0.5) * 1.2 = 0.6
        assert insight.urgency_score == 0.6
    
    def test_urgency_score_expires_later(self):
        """Test urgency score when expiring later."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        insight = VisionInsight(impact="medium", expires_at=expires_at)
        
        # No urgency multiplier
        assert insight.urgency_score == 0.5
    
    def test_urgency_score_capped_at_one(self):
        """Test urgency score is capped at 1.0."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        insight = VisionInsight(impact="critical", expires_at=expires_at)
        
        # critical (1.0) * 1.5 = 1.5, but capped at 1.0
        assert insight.urgency_score == 1.0
    
    def test_to_dict(self):
        """Test converting insight to dictionary."""
        insight_id = uuid4()
        objective_id = uuid4()
        task_id = uuid4()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=3)
        
        insight = VisionInsight(
            id=insight_id,
            type="opportunity",
            title="Cost Savings",
            description="Potential to reduce infrastructure costs",
            impact="medium",
            affected_objectives=[objective_id],
            affected_tasks=[task_id],
            suggested_actions=["Review cloud usage"],
            created_at=now,
            expires_at=expires_at,
            metadata={"estimated_savings": 10000}
        )
        
        result = insight.to_dict()
        
        assert result["id"] == str(insight_id)
        assert result["type"] == "opportunity"
        assert result["title"] == "Cost Savings"
        assert result["description"] == "Potential to reduce infrastructure costs"
        assert result["impact"] == "medium"
        assert result["affected_objectives"] == [str(objective_id)]
        assert result["affected_tasks"] == [str(task_id)]
        assert result["suggested_actions"] == ["Review cloud usage"]
        assert result["created_at"] == now.isoformat()
        assert result["expires_at"] == expires_at.isoformat()
        assert result["is_expired"] is False
        assert result["urgency_score"] == 0.6  # medium impact (0.5) * 1.2 (expires within week)
        assert result["metadata"] == {"estimated_savings": 10000}


class TestVisionDashboard:
    """Test cases for VisionDashboard value object."""
    
    def test_create_vision_dashboard_minimal(self):
        """Test creating vision dashboard with minimal data."""
        dashboard = VisionDashboard()
        
        assert isinstance(dashboard.timestamp, datetime)
        assert dashboard.total_objectives == 0
        assert dashboard.active_objectives == 0
        assert dashboard.completed_objectives == 0
        assert dashboard.overall_progress == 0.0
        assert dashboard.objectives_by_level == {}
        assert dashboard.objectives_by_status == {}
        assert dashboard.top_performing_objectives == []
        assert dashboard.at_risk_objectives == []
        assert dashboard.recent_completions == []
        assert dashboard.active_insights == []
        assert dashboard.alignment_summary == {}
    
    def test_create_vision_dashboard_full(self):
        """Test creating vision dashboard with all fields."""
        now = datetime.now(timezone.utc)
        insight = VisionInsight(title="Test Insight", type="recommendation")
        
        dashboard = VisionDashboard(
            timestamp=now,
            total_objectives=50,
            active_objectives=40,
            completed_objectives=10,
            overall_progress=75.5,
            objectives_by_level={"project": 30, "team": 20},
            objectives_by_status={"active": 40, "completed": 10},
            top_performing_objectives=[{"id": "obj-1", "progress": 95}],
            at_risk_objectives=[{"id": "obj-2", "days_overdue": 5}],
            recent_completions=[{"id": "obj-3", "completed_at": "2024-01-01"}],
            active_insights=[insight],
            alignment_summary={"high_alignment": 25, "low_alignment": 5}
        )
        
        assert dashboard.timestamp == now
        assert dashboard.total_objectives == 50
        assert dashboard.active_objectives == 40
        assert dashboard.completed_objectives == 10
        assert dashboard.overall_progress == 75.5
        assert dashboard.objectives_by_level == {"project": 30, "team": 20}
        assert dashboard.objectives_by_status == {"active": 40, "completed": 10}
        assert dashboard.top_performing_objectives == [{"id": "obj-1", "progress": 95}]
        assert dashboard.at_risk_objectives == [{"id": "obj-2", "days_overdue": 5}]
        assert dashboard.recent_completions == [{"id": "obj-3", "completed_at": "2024-01-01"}]
        assert len(dashboard.active_insights) == 1
        assert dashboard.alignment_summary == {"high_alignment": 25, "low_alignment": 5}
    
    def test_vision_dashboard_immutable(self):
        """Test that vision dashboard is immutable."""
        dashboard = VisionDashboard(total_objectives=10)
        
        with pytest.raises(AttributeError):
            dashboard.total_objectives = 20
    
    def test_to_dict(self):
        """Test converting dashboard to dictionary."""
        now = datetime.now(timezone.utc)
        insight = VisionInsight(title="Dashboard Insight", impact="high")
        
        dashboard = VisionDashboard(
            timestamp=now,
            total_objectives=25,
            active_objectives=20,
            completed_objectives=5,
            overall_progress=80.0,
            objectives_by_level={"project": 15, "team": 10},
            objectives_by_status={"active": 20, "completed": 5},
            top_performing_objectives=[{"id": "top-1", "progress": 98}],
            at_risk_objectives=[{"id": "risk-1", "issue": "delayed"}],
            recent_completions=[{"id": "done-1", "date": "2024-01-15"}],
            active_insights=[insight],
            alignment_summary={"strong": 18, "weak": 2}
        )
        
        result = dashboard.to_dict()
        
        assert result["timestamp"] == now.isoformat()
        
        # Summary section
        assert result["summary"]["total_objectives"] == 25
        assert result["summary"]["active_objectives"] == 20
        assert result["summary"]["completed_objectives"] == 5
        assert result["summary"]["overall_progress"] == 80.0
        
        # Breakdowns section
        assert result["breakdowns"]["by_level"] == {"project": 15, "team": 10}
        assert result["breakdowns"]["by_status"] == {"active": 20, "completed": 5}
        
        # Highlights section
        assert result["highlights"]["top_performing"] == [{"id": "top-1", "progress": 98}]
        assert result["highlights"]["at_risk"] == [{"id": "risk-1", "issue": "delayed"}]
        assert result["highlights"]["recent_completions"] == [{"id": "done-1", "date": "2024-01-15"}]
        
        # Insights section
        assert len(result["insights"]) == 1
        assert result["insights"][0]["title"] == "Dashboard Insight"
        
        # Alignment section
        assert result["alignment"] == {"strong": 18, "weak": 2}