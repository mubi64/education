// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transportation Fee Structure", {
  // refresh: function(frm) {

  // }

  select_all_months: function (frm) {
    frm.set_value("transportation_fee_structure_months", "");
    const monthNames = [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ];

    // / Creating a date object
    for (let i = 0; i < 12; i++) {
      let num = i < 9 ? "0" + (i + 1) : i + 1;
      frm.add_child("transportation_fee_structure_months", {
        month_number: num,
        month_name: monthNames[parseInt(num - 1)],
      });
      refresh_field("transportation_fee_structure_months");
    }
  },
});

frappe.ui.form.on("Transportation Fee Structure Months", {
  month_number: function (frm, cdt, cdn) {
    // frm.set_value("transportation_fee_structure_months", "");
    const child = locals[cdt][cdn];
    const monthNames = [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ];

    if (child.month_number) {
      child.month_name = monthNames[parseInt(child.month_number) - 1];
      frm.refresh_field("transportation_fee_structure_months"); // Refresh the child table field
    }
  },
});
