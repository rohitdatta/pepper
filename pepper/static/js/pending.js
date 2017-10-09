$(document).ready(function() {
	$('img.puppy')
		.mouseover(function () {
			$(this).attr('src', $SCRIPT_ROOT + '/static/img/cat-party.gif');
			$(this).css("object-fit", "cover");
		})
	.mouseout(function () {
		$(this).attr('src', $SCRIPT_ROOT +'/static/img/puppy.gif');
	});
});
