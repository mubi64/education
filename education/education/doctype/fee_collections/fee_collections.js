// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fee Collections", {
  // refresh: function(frm) {

  // }
  student: function (frm) {
    if (frm.doc.student) {
    }
  },
  get_student_details: function (frm) {
	frm.set_value("student_fee_details", "");
    if (frm.doc.student) {
      frappe.call({
        method: "education.education.api.get_student_fee_details",
        args: {
          student: frm.doc.student,
        },
        callback: function (r) {
          if (r.message) {
			console.log(r.message, "MESSAGE FOR FEE COLLECTION");
			for (let i = 0; i < r.message.length; i++) {
				var row = frappe.model.add_child(
				  frm.doc,
				  "student_fee_details"
				);
				const fee = r.message[i];
            	row.student_id = fee.student;
            	row.student_name = fee.student_name;
            	row.due_date = fee.due_date;
            	row.total_amount = fee.grand_total;
            	row.total_taxes_and_charges = fee.total_taxes_and_charges;
            	row.outstanding_amount = fee.outstanding_amount;
			}
        //     row.gross_amount = r.message.fee_amount;
        //     row.amount = r.message.fee_amount;
          }
          refresh_field("student_fee_details");
        //   frm.trigger("calculate_total_amount");
        },
      });
    }
    if (frm.doc.family_code) {
    }
  },
});
