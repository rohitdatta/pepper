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
        lengthMenu: [[-1], ["All"]]
    });
    $('#batch_email').on('submit', function (e) {
        var $currentForm = $(this);
        userTable.$('tr.selected').each(function () {
            $currentForm.append($('<input>')
                .attr('type', 'hidden')
                .attr('name', 'user_ids')
                .val($(this).find('#user_id').text()));
        });
    });
});
