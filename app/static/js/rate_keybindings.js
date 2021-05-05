// Help Modal
Mousetrap.bind(["?", "h"], function() {
  $("#helpModal").modal('toggle');
})

// Keybindings for Rating
Mousetrap.bind("0", function() {
  $("#rating-0").prop("checked", true).trigger("click");
})

Mousetrap.bind("1", function() {
  $("#rating-1").prop("checked", true).trigger("click");
})

Mousetrap.bind("2", function() {
  $("#rating-2").prop("checked", true).trigger("click");
})

Mousetrap.bind("3", function() {
  $("#rating-3").prop("checked", true).trigger("click");
})

// Open/Close Collapsible
Mousetrap.bind("c", function() {
  $("#collapseComment").collapse('toggle');
})

// Focus on textarea and fill button when collapsible opens
$("#collapseComment").on('show.bs.collapse', function() {
  $("#collapseButton").removeClass("btn-outline-info").addClass("btn-info");
})

$("#collapseComment").on('shown.bs.collapse', function() {
  $("#comment").focus();
})

// Return button to normal when collapse closes
$("#collapseComment").on('hide.bs.collapse', function() {
  $("#collapseButton").removeClass("btn-info").addClass("btn-outline-info");
})

// Previous image
Mousetrap.bind("left", function() {
  var plink = $("#prevPage")[0].getAttribute("href");
  if (plink != '#') {
    window.location.assign(plink)
  }
})

// Next image
Mousetrap.bind("right", function() {
  var nlink = $("#nextPage")[0].getAttribute("href");
  if (nlink != '#') {
    window.location.assign(nlink)
  }
})

// Zoom
var zoom;
Mousetrap.bind("z", function() {
  if ($(".img-magnifier-glass").length){
    $(".img-magnifier-glass").remove();
  } else {
    zoom = 2;
    magnify("img", zoom);
  }
})

Mousetrap.bind("shift+down", function() {
  if (zoom == 1.5) {
    $(".img-magnifier-glass").remove();
  } else {
    zoom -= .5;
    $(".img-magnifier-glass").remove();
    magnify("img", zoom);
  }
})

Mousetrap.bind("shift+up", function() {
  if ($(".img-magnifier-glass").is(':visible')) {
    zoom += .5;
    $(".img-magnifier-glass").remove();
    magnify("img", zoom);
  }
})
