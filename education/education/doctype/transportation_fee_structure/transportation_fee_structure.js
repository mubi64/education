// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transportation Fee Structure", {
  // refresh: function(frm) {

  // }

  select_all_months: function (frm) {
	frm.set_value("transportation_fee_structure_months", "");
    for (let i = 0; i < 12; i++) {
      frm.add_child("transportation_fee_structure_months", {
        month_number: i < 9 ? "0" + (i + 1) : i + 1,
      });
      refresh_field("transportation_fee_structure_months");
    }
  },
});
