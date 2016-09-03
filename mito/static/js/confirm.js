$('input[type=checkbox]').mousedown(function (event) {
    // Toggle checkstate logic
	alert('Hello');
    event.preventDefault(); // this would stop mousedown from continuing and would not focus
});