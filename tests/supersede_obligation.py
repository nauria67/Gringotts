from processors.obligation_processor import ObligationProcessor

audit_context = {
    "actor_type": "system",
    "actor_id": "admin_tool",
    "source": "manual_adjustment",
    "request_id": "req_supersede_4",
    "correlation_id": "obligation_adjustment:4",
    "causation_id": "manual_adjustment:4",
}

obligation = ObligationProcessor.get_obligation_by_id(obligation_id=4)

ObligationProcessor.supersede_obligation(
    obligation=obligation, new_amount=2000, audit_context=audit_context
)
