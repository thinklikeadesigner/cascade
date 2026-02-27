"""Tests for the reverse-cascade LangGraph state machine."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cascade_api.cascade.level_utils import (
    CascadeLevel,
    LEVELS_ASCENDING,
    discover_files,
    file_to_level,
    get_next_level_up,
    is_above,
)
from cascade_api.graph.state import Analysis, ApprovalResponse, FileChange


# ---------------------------------------------------------------------------
# Level utils
# ---------------------------------------------------------------------------


class TestLevelUtils:
    def test_levels_ascending_order(self):
        assert LEVELS_ASCENDING == ["day", "week", "month", "quarter", "year"]

    def test_get_next_level_up(self):
        assert get_next_level_up("day") == "week"
        assert get_next_level_up("week") == "month"
        assert get_next_level_up("month") == "quarter"
        assert get_next_level_up("quarter") == "year"
        assert get_next_level_up("year") is None

    def test_is_above(self):
        assert is_above("year", "day") is True
        assert is_above("month", "week") is True
        assert is_above("day", "year") is False
        assert is_above("week", "week") is False

    def test_file_to_level(self):
        assert file_to_level("week-feb14-20.md") == "week"
        assert file_to_level("feb-2026.md") == "month"
        assert file_to_level("jan-2025.md") == "month"
        assert file_to_level("q1-jan-feb-mar.md") == "quarter"
        assert file_to_level("q4-oct-nov-dec.md") == "quarter"
        assert file_to_level("2026-goals.md") == "year"
        assert file_to_level("day-feb-17.md") == "day"
        assert file_to_level("tracker.csv") is None
        assert file_to_level("adaptations.md") is None
        assert file_to_level("README.md") is None

    def test_discover_files(self, tmp_path):
        # Create some cascade files
        (tmp_path / "week-feb14-20.md").write_text("# Week plan")
        (tmp_path / "feb-2026.md").write_text("# February")
        (tmp_path / "q1-jan-feb-mar.md").write_text("# Q1")
        (tmp_path / "2026-goals.md").write_text("# Goals")
        (tmp_path / "tracker.csv").write_text("date,energy")  # not a cascade file

        files = discover_files(str(tmp_path))
        assert "week" in files
        assert "month" in files
        assert "quarter" in files
        assert "year" in files
        assert files["week"]["content"] == "# Week plan"
        assert files["year"]["content"] == "# Goals"

    def test_discover_files_missing_dir(self):
        with pytest.raises(FileNotFoundError):
            discover_files("/nonexistent/path")


# ---------------------------------------------------------------------------
# State models
# ---------------------------------------------------------------------------


class TestStateModels:
    def test_file_change(self):
        fc = FileChange(
            level="week",
            file_path="/data/week-feb14-20.md",
            original_content="old",
            new_content="new",
            summary="Updated week plan",
        )
        assert fc.level == "week"
        assert fc.summary == "Updated week plan"

    def test_analysis(self):
        a = Analysis(
            level="month",
            impact_summary="Shifted launch date",
            proposed_content="# Updated month",
            requires_propagation=True,
        )
        assert a.requires_propagation is True

    def test_approval_response(self):
        r = ApprovalResponse(decision="approve")
        assert r.decision == "approve"
        assert r.feedback is None

        r2 = ApprovalResponse(decision="modify", feedback="change the deadline")
        assert r2.feedback == "change the deadline"


# ---------------------------------------------------------------------------
# Graph nodes (with mocked LLM)
# ---------------------------------------------------------------------------


class TestGraphNodes:
    @pytest.mark.asyncio
    async def test_detect_change_level(self, tmp_path):
        # Setup cascade files
        (tmp_path / "week-feb14-20.md").write_text("# Week plan")
        (tmp_path / "feb-2026.md").write_text("# February")

        mock_response = json.dumps({"level": "week", "reasoning": "Task-level change"})

        with patch("cascade_api.graph.nodes.detect_change_level.ask", new_callable=AsyncMock) as mock_ask:
            mock_ask.return_value = mock_response

            from cascade_api.graph.nodes.detect_change_level import detect_change_level

            state = {
                "user_request": "Move Monday task to Wednesday",
                "data_dir": str(tmp_path),
                "api_key": "test-key",
            }

            result = await detect_change_level(state)

            assert result["origin_level"] == "week"
            assert result["current_level"] == "week"
            assert "week" in result["cascade_files"]
            mock_ask.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_impact(self):
        mock_response = json.dumps({
            "impactSummary": "Moved task to Wednesday",
            "proposedContent": "# Updated week",
            "requiresPropagation": False,
            "reasoning": "Week-only change",
        })

        with patch("cascade_api.graph.nodes.analyze_impact.ask", new_callable=AsyncMock) as mock_ask:
            mock_ask.return_value = mock_response

            from cascade_api.graph.nodes.analyze_impact import analyze_impact

            state = {
                "user_request": "Move Monday task to Wednesday",
                "api_key": "test-key",
                "current_level": "week",
                "cascade_files": {
                    "week": {"path": "/data/week.md", "content": "# Week plan"},
                },
                "applied_changes": [],
            }

            result = await analyze_impact(state)

            assert result["current_analysis"].level == "week"
            assert result["current_analysis"].requires_propagation is False
            assert "checkpoint_message" in result
            assert "WEEK" in result["checkpoint_message"]

    @pytest.mark.asyncio
    async def test_apply_changes(self, tmp_path):
        week_file = tmp_path / "week-feb14-20.md"
        week_file.write_text("# Original")

        from cascade_api.graph.nodes.apply_changes import apply_changes

        state = {
            "chat_jid": "test-thread",
            "data_dir": str(tmp_path),
            "current_analysis": Analysis(
                level="week",
                impact_summary="Updated tasks",
                proposed_content="# Updated week",
                requires_propagation=False,
            ),
            "cascade_files": {
                "week": {"path": str(week_file), "content": "# Original"},
            },
        }

        result = await apply_changes(state)

        assert len(result["applied_changes"]) == 1
        assert result["applied_changes"][0].level == "week"
        assert week_file.read_text() == "# Updated week"
        # Backup should have been created
        backup = tmp_path / "backups" / "test-thread" / "week-feb14-20.md"
        assert backup.exists()
        assert backup.read_text() == "# Original"

    @pytest.mark.asyncio
    async def test_handle_rejection(self, tmp_path):
        # Create a backup to restore
        backup_dir = tmp_path / "backups" / "test-thread"
        backup_dir.mkdir(parents=True)
        (backup_dir / "week.md").write_text("# Original")

        from cascade_api.graph.nodes.handle_rejection import handle_rejection

        state = {
            "chat_jid": "test-thread",
            "data_dir": str(tmp_path),
            "current_level": "week",
        }

        result = await handle_rejection(state)

        assert result["propagation_stopped"] is True
        assert "rejected" in result["checkpoint_message"]


# ---------------------------------------------------------------------------
# Graph edges
# ---------------------------------------------------------------------------


class TestGraphEdges:
    def test_route_approval_approve(self):
        from cascade_api.graph.edges.route_approval import route_approval

        state = {"last_approval_response": ApprovalResponse(decision="approve")}
        assert route_approval(state) == "apply_changes"

    def test_route_approval_reject(self):
        from cascade_api.graph.edges.route_approval import route_approval

        state = {"last_approval_response": ApprovalResponse(decision="reject")}
        assert route_approval(state) == "handle_rejection"

    def test_route_approval_modify(self):
        from cascade_api.graph.edges.route_approval import route_approval

        state = {"last_approval_response": ApprovalResponse(decision="modify")}
        assert route_approval(state) == "analyze_impact"

    def test_route_approval_stop(self):
        from cascade_api.graph.edges.route_approval import route_approval

        state = {"last_approval_response": ApprovalResponse(decision="stop")}
        assert route_approval(state) == "apply_changes"

    def test_should_propagate_stop_decision(self):
        from cascade_api.graph.edges.should_propagate import should_propagate

        state = {
            "last_approval_response": ApprovalResponse(decision="stop"),
            "current_analysis": Analysis(
                level="week",
                impact_summary="x",
                proposed_content="x",
                requires_propagation=True,
            ),
            "current_level": "week",
            "cascade_files": {"month": {"path": "/x", "content": "x"}},
        }
        assert should_propagate(state) == "__end__"

    def test_should_propagate_no_propagation(self):
        from cascade_api.graph.edges.should_propagate import should_propagate

        state = {
            "last_approval_response": ApprovalResponse(decision="approve"),
            "current_analysis": Analysis(
                level="week",
                impact_summary="x",
                proposed_content="x",
                requires_propagation=False,
            ),
            "current_level": "week",
            "cascade_files": {"month": {"path": "/x", "content": "x"}},
        }
        assert should_propagate(state) == "__end__"

    def test_should_propagate_continues(self):
        from cascade_api.graph.edges.should_propagate import should_propagate

        state = {
            "last_approval_response": ApprovalResponse(decision="approve"),
            "current_analysis": Analysis(
                level="week",
                impact_summary="x",
                proposed_content="x",
                requires_propagation=True,
            ),
            "current_level": "week",
            "cascade_files": {"month": {"path": "/x", "content": "x"}},
        }
        assert should_propagate(state) == "analyze_impact"

    def test_should_propagate_no_next_level(self):
        from cascade_api.graph.edges.should_propagate import should_propagate

        state = {
            "last_approval_response": ApprovalResponse(decision="approve"),
            "current_analysis": Analysis(
                level="year",
                impact_summary="x",
                proposed_content="x",
                requires_propagation=True,
            ),
            "current_level": "year",
            "cascade_files": {},
        }
        assert should_propagate(state) == "__end__"

    @pytest.mark.asyncio
    async def test_advance_level(self):
        from cascade_api.graph.edges.should_propagate import advance_level

        state = {"current_level": "week"}
        result = await advance_level(state)
        assert result["current_level"] == "month"
        assert result["current_analysis"] is None
        assert result["last_approval_response"] is None

    @pytest.mark.asyncio
    async def test_advance_level_at_top(self):
        from cascade_api.graph.edges.should_propagate import advance_level

        state = {"current_level": "year"}
        result = await advance_level(state)
        assert result["propagation_stopped"] is True


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


class TestGraphBuilder:
    def test_build_graph(self):
        from cascade_api.graph.graph import build_graph

        graph = build_graph()
        assert graph is not None
        # Should have all expected nodes
        # The compiled graph should be invokable (we don't call it here without mocks)
