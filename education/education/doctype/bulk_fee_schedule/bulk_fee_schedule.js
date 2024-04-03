// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bulk Fee Schedule", {
  refresh(frm) {},
  fee_structure: function (frm) {
    frm.set_value("components", []);
    if (frm.doc.fee_structure) {
      frappe.call({
        method: "education.education.api.get_fee_components",
        args: {
          fee_structure: frm.doc.fee_structure,
        },
        callback: function (r) {
          if (r.message) {
            $.each(r.message, function (i, d) {
              var row = frappe.model.add_child(
                frm.doc,
                "Fee Component",
                "components"
              );
              row.fees_category = d.fees_category;
              row.description = d.description;
              row.gross_amount = d.amount;
              row.amount = d.amount;
            });
            refresh_field("components");
          }
        },
      });
    }
  },

  taxes_and_charges: function (frm) {
    if (frm.doc.taxes_and_charges) {
      frm.set_value("taxes", "");
      frappe.call({
        method: "education.education.api.get_fee_sales_charges",
        args: {
          taxes_and_charges: frm.doc.taxes_and_charges,
        },
        callback: function (r) {
          if (r.message) {
            $.each(r.message, function (i, d) {
              var row = frappe.model.add_child(
                frm.doc,
                "Sales Taxes and Charges",
                "taxes"
              );
              row.charge_type = d.charge_type;
              row.account_head = d.account_head;
              row.rate = d.rate;
              row.included_in_print_rate = d.included_in_print_rate;
              row.base_total = d.base_total;
              row.cost_center = d.cost_center;
              row.description = d.description;
            });
          }
          refresh_field("taxes");
        },
      });
    }
  },

  show_months: function (frm) {
    // Array of month names
    frm.set_value("schedule_month", "");
    var months = [
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

    // Iterate over months and add rows to the child table
    for (var i = 0; i < frm.doc.nom; i++) {
      var row = frappe.model.add_child(
        frm.doc,
        "schedule_month",
        "schedule_month"
      );
      // Set the month value

      // Add the payment entry to the schedule
      row.posting_date = frappe.datetime.add_months(frm.doc.start_from, i);
      //   console.log(row.posting_date.getMonth());
      row.due_date = frappe.datetime.add_days(
        row.posting_date,
        frm.doc.period_day
      );
      var date_object = frappe.datetime.str_to_obj(row.posting_date.toString());

      // Get the month (returns 0-based index, so add 1 to get the actual month)
      var month_count = date_object.getMonth();
      var month = months[month_count];
      row.month = month;
    }

    // Refresh the child table to reflect the changes
    frm.refresh_field("schedule_month");
  },
});
