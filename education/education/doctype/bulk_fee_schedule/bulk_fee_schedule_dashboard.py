def get_data():
	return {
		"fieldname": "name",
		"non_standard_fieldnames": {
			"Fees": "bulk_fee_schedule",
		},
		"transactions": [{"items": ["Fees"]}],
	}