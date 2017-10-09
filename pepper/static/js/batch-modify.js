$(document).ready(function () {
	var userTable = $('#user_table').DataTable({
		order: [],
		lengthMenu: [[10, 50, 100, 500, -1], [10, 50, 100, 500, "All"]]
	});
});
