// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fee Discount Type", {
  refresh: function (frm) {
    // var com = frm.doc.discount;
    // for (var i = 0; i < com.length; i++) {
    //   var ele = com[i];
    //   if (ele.discount_type == "Amount") {
    //     ele.percentage = 0;
    //     frm.fields_dict.discount.grid.update_docfield_property(
    //       "amount",
    //       "read_only",
    //       0
    //     );
    //     frm.fields_dict.discount.grid.update_docfield_property(
    //       "percentage",
    //       "read_only",
    //       1
    //     );
    //   }

    //   if (ele.discount_type == "Percentage") {
    //     ele.discount_amount = 0;
    //     frm.fields_dict.discount.grid.update_docfield_property(
    //       "amount",
    //       "read_only",
    //       1
    //     );
    //     frm.fields_dict.discount.grid.update_docfield_property(
    //       "percentage",
    //       "read_only",
    //       0
    //     );
    //   }
    // }
    // refresh_field("discount");
  },
});

frappe.ui.form.on("Discount Item", {
	discount_type: function (frm) {
	  var com = frm.doc.discount;
	  for (var i = 0; i < com.length; i++) {
		var ele = com[i];
		if (ele.discount_type == "Amount") {
		  ele.percentage = 0;
		  frm.fields_dict.discount.grid.update_docfield_property(
			"amount",
			"read_only",
			0
		  );
		  frm.fields_dict.discount.grid.update_docfield_property(
			"percentage",
			"read_only",
			1
		  );
		}
  
		if (ele.discount_type == "Percentage") {
		  ele.amount = 0;
		  frm.fields_dict.discount.grid.update_docfield_property(
			"amount",
			"read_only",
			1
		  );
		  frm.fields_dict.discount.grid.update_docfield_property(
			"percentage",
			"read_only",
			0
		  );
		}
	  }
	  refresh_field("discount");
	},
  });
  
