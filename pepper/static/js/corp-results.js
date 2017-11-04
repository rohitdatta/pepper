$(document).ready(function() {
    var table = $('#result-table').DataTable({
        lengthMenu: [[10, 50, 100, 500, -1], [10, 50, 100, 500, "All"]],
        paging: true,
        ordering: true,
        searching: false,
        columnDefs: [
            {
                targets: [5],
                orderable: false
            }
        ]
    });
});
