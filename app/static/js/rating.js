/// Variables/constants
// Rating Buttons
const rateBtns = [
  $("#rating-0"), $("#rating-1"), $("#rating-2"), $("#rating-3")
]
// Zoom level
let zoom;

// Subratings JSON submitted by Flask from MySQL database
let subratings = JSON.parse('{{ subratings_data | tojson | safe }}');
// {id: model_ID, selected: Boolean, rating: [0-3], keybinding: [asc]_\S}

/// Functions
// Click rating
function clickRating(rating) {
  rateBtns[rating].trigger("click")
}

// Click subrating
function clickSubrating(id) { $(`#subrating_${id}`).trigger("click") }

// Actions for subrating buttons
function toggleSubrating(obj) {
// When clicking on subrating button:
  // 1 Toggle 'selected' boolean
  // 2 Toggle active status
  // 3 Toggle signal in corresponding rating
  let sr = subratings.filter(sr => sr.id == obj.attr("id").split("_")[1])[0];
  let rateBtn = $(`label[for=${rateBtns[sr.rating].attr("id")}`)

  if (subrating.selected) {
    sr.selected = false;
    obj.removeClass("active");
    rateBtn.text().includes("*") || rateBtn.text(rateBtn.text() + "*")
  } else {
    sr.selected = true;
    obj.addClass("active");
    subratings.filter(
      ({selected, rating}) => selected === false & rating === sr.rating
    ).length === 0 && rateBtn.text().includes("*") &&
      rateBtn.text(rateBtn.text().slice(0,-1));
  }
}

function submitSubratings() {
  let subratingData = []
  subratings.forEach(sr => subratingData.push(`${sr.id}_${sr.selected}`));
  $("#subratingsForm").val(subratingData.join("___"))
}

/// Mousetrap Keybindings
// Help Modal
Mousetrap.bind(["?", "h"], () => $("#helpModal").modal('toggle'))

// Keybindings for Rating
Mousetrap.bind("0", () => clickRating(0));
Mousetrap.bind("1", () => clickRating(1));
Mousetrap.bind("2", () => clickRating(2));
Mousetrap.bind("3", () => clickRating(3));

// Open/Close Collapsible Comment Textarea
Mousetrap.bind("c", () => $("#collapseComment").collapse('toggle'))

// Go back to previous RATED image
Mousetrap.bind(["ctrl+z", "u"], () => $("#backButton").click())

// Previous image
Mousetrap.bind("left", () => {
  ($("#prevPage")[0].getAttribute("href") != '#')
    && window.location.assign(plink)
})

// Next image
Mousetrap.bind("right", () => {
  ($("#nextPage")[0].getAttribute("href") != '#')
    && window.location.assign(nlink)
})

// Zoom
Mousetrap.bind("z", () => {
  if ($(".img-magnifier-glass").length){
    $(".img-magnifier-glass").remove();
  } else {
    zoom = 2;
    magnify("img", zoom);
  }
})

Mousetrap.bind("shift+down", () => {
  if (zoom == 1.5) {
    $(".img-magnifier-glass").remove();
  } else {
    zoom -= .5;
    $(".img-magnifier-glass").remove();
    magnify("img", zoom);
  }
})

Mousetrap.bind("shift+up", () => {
  if ($(".img-magnifier-glass").is(':visible')) {
    zoom += .5;
    $(".img-magnifier-glass").remove();
    magnify("img", zoom);
  }
})

/// Actions
// Focus on textarea and fill button when collapsible opens
$("#collapseComment").on('show.bs.collapse', () => {
  $("#collapseButton").addClass("active"); $("#comment").focus();
});

// Return button to normal when collapse closes
$("#collapseComment").on('hide.bs.collapse',
  () => $("#collapseButton").removeClass("active"));

// Mark already selected from Backend & Set-Up Mousetrap
subratings.forEach(
  subrating => {
    subrating.selected && $("#subrating_" + subrating.id).addClass('active');
    kb = subrating.keybinding.split("_");
    let [mod, kb] = (kb === 2) ? kb : [null, kb[0]];
    let key;
    switch (mod) {
      case "a": key = `alt+${kb}`; break;
      case "c": key = `ctrl+${kb}`; break;
      case "s": key = `shift+${kb}`; break;
      default: key = kb;
    };
    Mousetrap.bind(key, () => clickSubrating(subrating.id));
  }
);

// Toggle subrating button
$("button[id^=subrating]").each(function(index){
  $(this).click(() => toggleSubrating($(this)))
});

/// Submit Form
//Force submit with shif-enter:
Mousetrap.bind(
  "shift+enter", () => {
    submitSubratings();
    $("form").submit();
  }
);

// Submit form when changes:
$(".form-check").change(() => {submitSubratings(); $("form").submit();})

//Submit rate (Comment)
$("textarea").change(() => {submitSubratings(); $("form").submit();})
