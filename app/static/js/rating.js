/// Variables/constants
// Rating Buttons
const rateBtns = [
  $("#rating-0"), $("#rating-1"), $("#rating-2"), $("#rating-3")
]
// Zoom level
let zoom;

// Subratings JSON submitted by Flask from MySQL database
// {id: model_ID, selected: Boolean, rating: [0-3], keybinding: [asc]_\S}

/// Functions
// Go To specific page
function goToPage(page) {
  let url = window.location.href;
  let newUrl
  const rex = new RegExp("page=\d+");
  if (rex.test(url)) {
    newUrl = url.replace(rex, `page=${page}`);
  } else {
    newUrl = url.replace("\?", `?page=${page}&`);
  }
  console.log(newUrl);
  window.location.assign(newUrl);
}

// Click rating
function clickRating(rating) {
  rateBtns[rating].trigger("click")
}

// Click subrating
function clickSubrating(id) { $(`#subrating_${id}`).trigger("click") }

// subrating signalling
function subratingSignal(state, rateBtn, sr_rating = null) {
  switch (state) {
    case "on":
      rateBtn.text().includes("*") || rateBtn.text(rateBtn.text() + "*");
      break;
    case "off":
      subratings.filter(
        ({selected, rating}) => selected === true & rating === sr_rating)
        .length === 0 &&
        rateBtn.text().includes("*") &&
        rateBtn.text(rateBtn.text().slice(0,-1));
  };
}

// Actions for subrating buttons
function toggleSubrating(obj) {
// When clicking on subrating button:
  // 1 Toggle 'selected' boolean
  // 2 Toggle active status
  // 3 Toggle signal in corresponding rating
  let sr = subratings.filter(sr => sr.id == obj.attr("id").split("_")[1])[0];
  let rateBtn = $(`label[for=${rateBtns[sr.rating].attr("id")}`)

  if (sr.selected) {
    sr.selected = false;
    obj.removeClass("active");
    subratingSignal("off", rateBtn, sr.rating)
  } else {
    sr.selected = true;
    obj.addClass("active");
    subratingSignal("on", rateBtn)
  }
};

function submitSubratings() {
  let subratingData = []
  subratings.forEach(sr => subratingData.push(`${sr.id}_${sr.selected}`));
  $("#subratingsForm").val(subratingData.join("___"))
};

function submitAll() {submitSubratings(); $("form").submit();};

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
// Go to specific page
$("#goToPageBtn").click(() => {
  submitAll();
  goToPage($("#goToPageInput").val());
});

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
    let obj = $("#subrating_" + subrating.id)
    let rateBtn = $(`label[for=${rateBtns[subrating.rating].attr("id")}`)
    subrating.selected &&
      obj.addClass('active') &&
      subratingSignal("on", rateBtn);
    let key, mod
    let kb = (subrating.keybinding) ? subrating.keybinding.split("_") : [""];
    [mod, kb] = (kb.length === 2) ? kb : [null, kb[0]];
    switch (mod) {
      case "a": key = `alt+${kb}`; break;
      case "c": key = `ctrl+${kb}`; break;
      case "s": key = `shift+${kb}`; break;
      default: key = kb;
    };
    console.log(`Mousetrap.bind(${key}, () => clickSubrating(${subrating.id}))`)
    if (key) Mousetrap.bind(key, () => clickSubrating(subrating.id));
  }
);

// Toggle subrating button
$("button[id^=subrating]").each(function(index){
  $(this).click(() => toggleSubrating($(this)))
});

/// Submit Form
// Submit button
$("#submitButton").click(() => submitAll());

//Force submit with shif-enter:
Mousetrap.bind("shift+enter", () => submitAll());

// Submit form when changes:
$(".form-check").change(() => submitAll())

//Submit rate (Comment)
$("textarea").change(() => submitAll())
