from processors.obligation_processor import ObligationProcessor

obligation = ObligationProcessor.get_obligation_by_id(obligation_id=4)

ObligationProcessor.supersede_obligation(obligation=obligation, new_amount=2000)
