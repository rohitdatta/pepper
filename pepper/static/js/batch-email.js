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
		order: [[1, 'asc']],
		lengthMenu: [[10, 50, 100, 500, -1], [10, 50, 100, 500, "All"]]
	});
	$('#batch_email').on('submit', function (e) {
		var $currentForm = $(this);
		userTable.$('tr.selected').each(function () {
			$currentForm.append($('<input>')
				.attr('type', 'hidden')
				.attr('name', 'user_ids')
				.val($(this).find('.user_id').text()));
		});
	});

	function contextMenuAction(action, opt) {
		if (action === 'select') {
			userTable.row(opt.$trigger).select();
			return true;
		}
		if (action === 'deselect') {
			userTable.row(opt.$trigger).deselect();
			return true;
		}
		var val = opt.$trigger.text();
		userTable.column(opt.$trigger).nodes().each(function (el) {
			if ($(el).text() === val) {
				if (action === 'selectAll') {
					userTable.row(el).select();
				} else if (action === 'deselectAll') {
					userTable.row(el).deselect();
				}
			}
		});

		return true;
	}

	$.contextMenu({
		selector: ".data-item",
		items: {
			select: {
				name: "Select this row",
			},
			deselect: {
				name: "Unselect this row",
			},
			selectAll: {
				name: "Select all items matching this attribute",
			},
			deselectAll: {
				name: "Unselect all items matching this attribute",
			}
		},
		callback: contextMenuAction
	});
});
