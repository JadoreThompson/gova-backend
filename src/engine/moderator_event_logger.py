from sqlalchemy.orm import Session

from enums import ModeratorEventType, LogSeverity, ActionStatus
from core.events import (
    ModeratorEvent,
    StartModeratorEvent,
    KillModeratorEvent,
    DeadModeratorEvent,
    ErrorModeratorEvent,
    ActionPerformedModeratorEvent,
    EvaluationCreatedModeratorEvent,
)
from db_models import ModeratorEventLogs


class ModeratorEventLogger:
    """Handles persistence of all moderator deployment events."""

    _instance = None

    def __new__(cls, *args, **kw):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db: Session):
        if hasattr(self, "_initialised") and self._initialised:
            return

        self.db = db
        self._handlers = {
            ModeratorEventType.START: self._handle_start,
            ModeratorEventType.ALIVE: self._handle_alive,
            ModeratorEventType.KILL: self._handle_stop,
            ModeratorEventType.DEAD: self._handle_stopped,
            ModeratorEventType.FAILED: self._handle_failed,
            ModeratorEventType.HEARTBEAT: self._handle_heartbeat,
            ModeratorEventType.ACTION_PERFORMED: self._handle_action,
            ModeratorEventType.EVALUATION_CREATED: self._handle_evaluation,
            ModeratorEventType.ERROR: self._handle_error,
            ModeratorEventType.WARNING: self._handle_warning,
        }
        self._initialised = True

    def log_event(self, event: ModeratorEvent) -> ModeratorEventLogs:
        """Log a moderator deployment event."""
        handler = self._handlers.get(event.type)
        if not handler:
            self._create_generic_log(event)
        handler(event)

    def _handle_start(self, event: StartModeratorEvent):
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message=f"Moderator started on {event.platform.value}",
            details={"config": event.conf.to_serialisable_dict()},
        )

    def _handle_alive(self, event: ModeratorEvent):
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message=f"Moderator alive",
        )

    def _handle_stop(self, event: KillModeratorEvent):
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message="Moderator stop requested",
            details={"reason": event.reason or "unspecified"},
        )

    def _handle_stopped(self, event: DeadModeratorEvent):
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message="Moderator stopped",
            details={"reason": event.reason or "unknown"},
        )

    def _handle_failed(self, event: ModeratorEvent):
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.CRITICAL,
            message="Moderator failed",
        )

    def _handle_heartbeat(self, event: ModeratorEvent):
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message="Moderator heartbeat received",
        )

    def _handle_action(self, event: ActionPerformedModeratorEvent):
        """Handle all action-related events by dispatching based on status."""
        status_handlers = {
            ActionStatus.SUCCESS: self._handle_action_success,
            ActionStatus.FAILED: self._handle_action_failed,
            ActionStatus.AWAITING_APPROVAL: self._handle_action_pending,
            ActionStatus.DECLINED: self._handle_action_declined,
            ActionStatus.APPROVED: self._handle_action_approved,
        }

        handler = status_handlers.get(event.status)
        if handler:
            return handler(event)

        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.WARNING,
            message=f"Action '{event.action_type}' with unhandled status '{event.status.value}'",
            action_type=str(event.action_type),
            action_params=event.params.to_serialisable_dict(),
            action_status=event.status,
            context=event.context.to_serialisable_dict(),
        )

    def _handle_action_success(self, event: ActionPerformedModeratorEvent):
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message=f"Action '{event.action_type}' executed successfully",
            action_type=str(event.action_type),
            action_params=event.params.to_serialisable_dict(),
            action_status=ActionStatus.SUCCESS,
            context=event.context.to_serialisable_dict(),
        )

    def _handle_action_failed(self, event: ActionPerformedModeratorEvent):
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.ERROR,
            message=f"Action '{event.action_type}' failed",
            action_type=str(event.action_type),
            action_params=event.params.to_serialisable_dict(),
            action_status=event.status,
            context=event.context.to_serialisable_dict(),
        )

    def _handle_action_pending(self, event: ActionPerformedModeratorEvent):
        message = (
            f"Action '{event.action_type}' awaiting approval"
            if event.status == ActionStatus.AWAITING_APPROVAL
            else f"Action '{event.action_type}' is pending"
        )
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.WARNING,
            message=message,
            action_type=str(event.action_type),
            action_params=event.params.to_serialisable_dict(),
            action_status=event.status,
            context=event.context.to_serialisable_dict(),
        )

    def _handle_action_approved(self, event: ActionPerformedModeratorEvent):
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message=f"Action '{event.action_type}' was approved",
            action_type=str(event.action_type),
            action_params=event.params.to_serialisable_dict(),
            action_status=ActionStatus.APPROVED,
            context=event.context.to_serialisable_dict(),
        )

    def _handle_action_declined(self, event: ActionPerformedModeratorEvent):
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.WARNING,
            message=f"Action '{event.action_type}' was declined",
            action_type=str(event.action_type),
            action_params=event.params.to_serialisable_dict(),
            action_status=ActionStatus.DECLINED,
            context=event.context.to_serialisable_dict(),
        )

    def _handle_evaluation(self, event: EvaluationCreatedModeratorEvent):
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message="Evaluation created",
            details={
                "evaluation": event.evaluation.to_serialisable_dict(),
                "context": event.context.to_serialisable_dict(),
            },
            message_id=event.message_id,
            context=event.context.to_serialisable_dict(),
        )

    def _handle_error(self, event: ErrorModeratorEvent):
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.ERROR,
            message="Moderator error occurred",
            stack_trace=event.stack_trace,
        )

    def _handle_warning(self, event: ModeratorEvent):
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.WARNING,
            message="Warning event logged",
        )

    def _create_generic_log(self, event: ModeratorEvent):
        """Fallback for unrecognized event types."""
        return self._create_log(
            moderator_id=event.moderator_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message=f"Unhandled event type: {event.type}",
            details=event.to_serialisable_dict(),
        )

    def _create_log(
        self,
        event_type,
        message,
        moderator_id=None,
        severity=LogSeverity.INFO,
        details=None,
        action_type=None,
        action_params=None,
        action_status=None,
        context=None,
        error_message=None,
        stack_trace=None,
        message_id=None,
    ):
        """Persist log record to DB."""
        log = ModeratorEventLogs(
            moderator_id=moderator_id,
            event_type=event_type.value,
            severity=severity.value,
            message=message,
            details=details,
            action_type=action_type,
            action_params=action_params,
            action_status=action_status.value if action_status else None,
            context=context,
            error_message=error_message,
            stack_trace=stack_trace,
            message_id=message_id,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
