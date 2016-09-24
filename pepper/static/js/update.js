$(function () {
	$("#refresh").click(function() {
		$.ajax({
			url: '/refresh',
			method: 'GET',
			beforeSend: function () {
				$("#refresh").prop("disabled", true);
			},
			success: function (data) {
				$("#dietary-restrictions").text(data.dietary_restrictions);
				if (data.special_needs != null) {
					$("#special-needs").text(data.special_needs);
				} else {
					$("#special-needs").text("None");
				}
				toastr.success('Updated information from MyMLH successfully');
				$("#refresh").prop("disabled", false);
		},
			error: function () {
				toastr.error('Failed to connect to MyMLH. Please try again later');
				$("#refresh").prop("disabled", false);
			}
		});
	});
});