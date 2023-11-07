def get_data():
	return {
		"fieldname": "name",
		"non_standard_fieldnames": {
			"Journal Entry": "reference_name",
		},
		"transactions": [{"items": ["Journal Entry"]}],
	}