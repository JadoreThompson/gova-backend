from datetime import datetime
from sqlalchemy.orm import Session

from db_models import ModeratorDeploymentEventLogs
from core.enums import (
    ModeratorDeploymentEventType,
    LogSeverity,
    ActionStatus,
)
from core.events import (
    ModeratorDeploymentEvent,
    StartModeratorDeploymentEvent,
    StartedModeratorDeploymentEvent,
    StopModeratorDeploymentEvent,
    StoppedModeratorDeploymentEvent,
    ErrorModeratorDeploymentEvent,
    ActionModeratorDeploymentEvent,
    EvaluationModeratorDeploymentEvent,
)


class ModeratorDeploymentEventLogger:
    """Handles persistence of all moderator deployment events."""

    def __init__(self, db: Session):
        self.db = db
        self._handlers = {
            ModeratorDeploymentEventType.DEPLOYMENT_START: self._handle_start,
            ModeratorDeploymentEventType.DEPLOYMENT_ALIVE: self._handle_alive,
            ModeratorDeploymentEventType.DEPLOYMENT_STOP: self._handle_stop,
            ModeratorDeploymentEventType.DEPLOYMENT_DEAD: self._handle_stopped,
            ModeratorDeploymentEventType.DEPLOYMENT_FAILED: self._handle_failed,
            ModeratorDeploymentEventType.DEPLOYMENT_HEARTBEAT: self._handle_heartbeat,
            ModeratorDeploymentEventType.ACTION_PERFORMED: self._handle_action,
            ModeratorDeploymentEventType.EVALUATION_CREATED: self._handle_evaluation,
            ModeratorDeploymentEventType.ERROR: self._handle_error,
            ModeratorDeploymentEventType.WARNING: self._handle_warning,
        }

    # --------------------------------------------------------------------------
    # Public
    # --------------------------------------------------------------------------
    def log_event(self, event: ModeratorDeploymentEvent) -> ModeratorDeploymentEventLogs:
        """Log a moderator deployment event."""
        handler = self._handlers.get(event.type)
        if not handler:
            return self._create_generic_log(event)
        return handler(event)

    # --------------------------------------------------------------------------
    # Deployment lifecycle
    # --------------------------------------------------------------------------
    def _handle_start(self, event: StartModeratorDeploymentEvent):
        return self._create_log(
            moderator_id=event.moderator_id,
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message=f"Deployment started on {event.platform.value}",
            details={"config": event.moderator_conf.model_dump()},
        )

    def _handle_alive(self, event: StartedModeratorDeploymentEvent):
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message=f"Deployment alive (server_id={event.server_id})",
        )

    def _handle_stop(self, event: StopModeratorDeploymentEvent):
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message="Deployment stop requested",
            details={"reason": event.reason or "unspecified"},
        )

    def _handle_stopped(self, event: StoppedModeratorDeploymentEvent):
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message="Deployment stopped",
            details={"reason": event.reason or "unknown"},
        )

    def _handle_failed(self, event: ModeratorDeploymentEvent):
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.CRITICAL,
            message="Deployment failed",
        )

    def _handle_heartbeat(self, event: ModeratorDeploymentEvent):
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message="Deployment heartbeat received",
        )

    # --------------------------------------------------------------------------
    # Actions
    # --------------------------------------------------------------------------
    def _handle_action(self, event: ActionModeratorDeploymentEvent):
        """Handle all action-related events by dispatching based on status."""
        status_handlers = {
            ActionStatus.SUCCESS: self._handle_action_success,
            ActionStatus.FAILED: self._handle_action_failed,
            ActionStatus.PENDING: self._handle_action_pending,
            ActionStatus.AWAITING_APPROVAL: self._handle_action_pending,
            ActionStatus.DECLINED: self._handle_action_declined,
            ActionStatus.APPROVED: self._handle_action_approved,
        }
        handler = status_handlers.get(event.status)
        if handler:
            return handler(event)

        # Fallback for any unknown status
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.WARNING,
            message=f"Action '{event.action_type}' with unhandled status '{event.status.value}'",
            action_type=str(event.action_type),
            action_params=event.params.model_dump(),
            action_status=event.status,
        )

    def _handle_action_success(self, event: ActionModeratorDeploymentEvent):
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message=f"Action '{event.action_type}' executed successfully",
            action_type=str(event.action_type),
            action_params=event.params.model_dump(),
            action_status=ActionStatus.SUCCESS,
        )

    def _handle_action_failed(self, event: ActionModeratorDeploymentEvent):
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.ERROR,
            message=f"Action '{event.action_type}' failed",
            action_type=str(event.action_type),
            action_params=event.params.model_dump(),
            action_status=event.status,
        )

    def _handle_action_pending(self, event: ActionModeratorDeploymentEvent):
        message = (
            f"Action '{event.action_type}' awaiting approval"
            if event.status == ActionStatus.AWAITING_APPROVAL
            else f"Action '{event.action_type}' is pending"
        )
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.WARNING,
            message=message,
            action_type=str(event.action_type),
            action_params=event.params.model_dump(),
            action_status=event.status,
        )

    def _handle_action_approved(self, event: ActionModeratorDeploymentEvent):
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message=f"Action '{event.action_type}' was approved",
            action_type=str(event.action_type),
            action_params=event.params.model_dump(),
            action_status=ActionStatus.APPROVED,
        )

    def _handle_action_declined(self, event: ActionModeratorDeploymentEvent):
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.WARNING,
            message=f"Action '{event.action_type}' was declined",
            action_type=str(event.action_type),
            action_params=event.params.model_dump(),
            action_status=ActionStatus.DECLINED,
        )

    # --------------------------------------------------------------------------
    # Evaluations
    # --------------------------------------------------------------------------
    def _handle_evaluation(self, event: EvaluationModeratorDeploymentEvent):
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message="Evaluation created",
            details={
                "evaluation": event.evaluation.model_dump(),
                "context": event.context.model_dump(),
            },
        )

    # --------------------------------------------------------------------------
    # Errors / Warnings
    # --------------------------------------------------------------------------
    def _handle_error(self, event: ErrorModeratorDeploymentEvent):
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.ERROR,
            message="Deployment error occurred",
            stack_trace=event.stack_trace,
        )

    def _handle_warning(self, event: ModeratorDeploymentEvent):
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.WARNING,
            message="Warning event logged",
        )

    # --------------------------------------------------------------------------
    # Generic / fallback handler
    # --------------------------------------------------------------------------
    def _create_generic_log(self, event: ModeratorDeploymentEvent):
        """Fallback for unrecognized event types."""
        return self._create_log(
            deployment_id=event.deployment_id,
            event_type=event.type,
            severity=LogSeverity.INFO,
            message=f"Unhandled event type: {event.type}",
            details=event.model_dump(),
        )

    # --------------------------------------------------------------------------
    # Shared persistence helper
    # --------------------------------------------------------------------------
    def _create_log(
        self,
        event_type,
        message,
        deployment_id=None,
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
        log = ModeratorDeploymentEventLogs(
            moderator_id=moderator_id,
            deployment_id=deployment_id,
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