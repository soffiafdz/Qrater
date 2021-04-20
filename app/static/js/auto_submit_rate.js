// Submit Form
function submitRating() {
  document.getElementById("ratingForm").submit();
}

// Submit on change of Rating/Comment
$(".rating-radio").change(function(){
  $("form").submit();
})

$("textarea").change(function(){
  $("form").submit();
})
