// Keybindings for Rating
Mousetrap.bind("0", function() {
  $("#rating-0").prop("checked", true).trigger("click");
})

Mousetrap.bind("down", function() {
  $("#collapseComment").collapse({'show'})
})

Mousetrap.bind("up", function() {
  $("#collapseComment").collapse({'hide'})
})
