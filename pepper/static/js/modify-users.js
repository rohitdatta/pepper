$(document).ready(function () {
	var userTable = $('#user_table').DataTable({
		columnDefs: [{
			orderable: false,
			className: 'select-checkbox',
			targets: 0
		}],
		select: {
			style: 'os',
			selector: 'td:first-child'
		},
		order: [],
		lengthMenu: [[10, 50, 100, 500, -1], [10, 50, 100, 500, "All"]]
	});
	$('#batch_users').on('submit', function (e) {
		var $currentForm = $(this);
		userTable.$('tr.selected').each(function () {
			$currentForm.append($('<input>')
				.attr('type', 'hidden')
				.attr('name', 'user_ids')
				.val($(this).find('.user_id').text()));
		});
	});
});
