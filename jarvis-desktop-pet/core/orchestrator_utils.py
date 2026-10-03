from core.bus import Event, MessageBus, create_event
from core.handoff import HandoffEvent


async def handoff(bus: MessageBus, h: HandoffEvent):
    ev = create_event(
        topic=f"orchestrator.handoff.{h.to_agent}",
        etype="handoff",
        payload={
            "from": h.from_agent,
            "to": h.to_agent,
            "task_id": h.task_id,
            "context": h.context,
            "deps": h.deps,
            "expected_outputs": h.expected_outputs,
        },
        correlation_id=h.correlation_id or h.id,
        ttl_ms=h.ttl_ms,
        source=h.from_agent,
        target=h.to_agent,
    )
    await bus.publish(ev)
