# 18. IPC & MESSAGE BUS

Async pub/sub, event-driven, typed JSON. Topics: input.*, intent.*, orchestrator.*, gent.*, 	ool.*, ision.*, safety.*, oice.*, memory.*, pet.*, state.*

## 18.1 Schema
Event: {event_id,type,ts,source,target,correlation_id,ttl,payload,meta}
Handoff: delegation with deps/ttl
## 18.2 Guarantees
At-most-once/ordered per topic, async, non-blocking, backpressure.
## 18.3 Transport
In-process (asyncio.Queue) + pub/sub. Simple, fast, local.
