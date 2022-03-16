// Subratings management

// Variables
const addBtn = $("#subratingAddBtn");
const delBtn = $("#subratingDelBtn");
const subrText = $("#subratingText");
const subrKb = $("#subrKeybinding");
const kbMods = [$("#kbAlt"), $("#kbCtrl"), $("#kbShift")]
const rateBtns = [
  $("#subrPend"), $("#subrPass"), $("#subrWarn"), $("#subrFail"),
];

let subrating = "0";
let subratings = [];
let colors = ["dark", "success", "warning", "danger"];
let existing = false;
let origId = "new";
let kbMod = null;
let origText, origKb, origRating
let subratingChange = false


// Functions

// Change Add <-> Save
function btn_toggle(text) {
  if (text === undefined) {
    addBtn.html() === "Add" ? addBtn.html("Save") : addBtn.html("Add");
  } else {
    addBtn.html() !== text && addBtn.html(text)
  }
}

// Add subrating box
function addSubrating(text, rating, keyBinding, id, edit) {
  // Check ID
  id === "new" && (id = `srating_n${subratings.length + 1}`)

  // If Saving, change HTML; revert back to Add & hide delete button
  if (edit) {
    let obj = $("#" + String(id));
    obj.html(text);
    let completeKb = (origKb.length === 1) ? origKb[0] : origKb.join("_")
    if (completeKb !== keyBinding) {
      obj.removeClass(
        "Keybinding_" + completeKb
      ).addClass(
        "Keybinding_" + keyBinding
      );
    }
    origRating = obj.attr("class").match(
      /list-group-item-\w+/g)[1].split("-")[3];
    if (origRating !== colors[rating]) {
      obj.removeClass(
        "list-group-item-" + origRating
      ).addClass(
        "list-group-item-" + colors[rating]
      );
    }

    $.each(subratings, function() {
      if (this.id === String(id)) {
        this.text = text;
        this.rating = rating;
        this.keyBinding = keyBinding;
      }
    })

  } else {
    // Add to Array
    subratings.push({
      id: id, text: text, rating: rating, keyBinding: keyBinding
    });

    // Add list-group-item
    $("#subratingsBar").append(
      `<a href="#"
      id="${id}"
      class="list-group-item list-group-item-action list-group-item-${colors[rating]} Keybinding_${keyBinding}"
      >${text}</a>
      `
    );
    $("#" + id).click(function() {activateSubrating($(this))});
  }

  // Revert back to normal
  clearForm();
};

function deactivateSubratings() {
  $(".list-group-item-action").each(function(index) {
    $(this).removeClass("active")
  });
}

function deleteSubrating(obj) {
// To delete a subrating:
  // 1 Mark "to-delete" order for Backend
  $.each(subratings,
    function() {if (this.id === obj.attr("id")) this.toDelete = true}
  );
  obj.remove(); // 2 Remove button
  clearForm();  // 3 Clear form
}

function activateSubrating(obj) {
// When clicking on an existing subrating:
// 1 highlight it
// 2 extract values
// 3 fill form fields
// 4 add delete button

  // If btn (obj) already active; deactivate it and clear form (w/o saving)
  if (obj.attr("class").includes("active")) {
    clearForm();
  } else {
    // Deactivate every button
    deactivateSubratings();

    // Activate this one
    obj.addClass("active");

    // Extract values from it
    existing = true;
    btn_toggle("Save");
    addBtn.removeAttr("disabled");
    origId = obj.attr("id");
    origText = obj.html();
    let kb = obj.attr("class").match(/Keybinding_\S+/);
    // ADJUST AFTER MOD
    origKb = (kb) ? kb[0].split("_").slice(1) : [""];
    origRating = colors.indexOf(
      obj.attr("class").match(/list-group-item-\w+/g)[1].split("-")[3]
    );

    // Fill form
    subrText.val(origText);
    // ADJUST AFTER MOD
    if (origKb.length > 1) {
      toggleKbMod(origKb[0]);
      subrKb.val(origKb[1]);
    } else {
      subrKb.val(origKb[0]);
    }
    toggleRatings(origRating);

    // "Delete" button
    delBtn.show();
  }
}

function toggleKbMod(mod=null) {
  // If no argument, clear form
  if (mod === null) {
    kbMods.forEach(btn => btn.removeClass("active"));
    kbMod = null;
  } else {
    let selected = kbMods.filter(btn => btn.val() === mod)[0];
    // If already selected, "disactivate" it
    if (kbMod === selected.val()) {
      selected.removeClass("active");
      kbMod = null;
    } else {
      kbMods.forEach(btn => btn.removeClass("active"));
      selected.addClass("active");
      kbMod = selected.val();
    }
  }
}

function toggleRatings(rating) {
  subrating = (rating === undefined) ? $(this).val()[0] : rating
  selected = rateBtns.filter(btn => btn.val() == subrating)[0];
  let toDeactivate = rateBtns.filter(btn => btn.val() !== subrating);
  toDeactivate.forEach(btn => btn.removeClass("active"));
  selected.addClass("active");
}

function clearForm() {
  btn_toggle("Add");
  delBtn.hide();
  subrText.val("");
  subrKb.val("");
  toggleRatings("0");
  toggleKbMod();
  origId = "new";
  existing = false;
  deactivateSubratings();
}

//subratings :
//{ id: id, text: text, rating: rating, keyBinding: keyBinding; delete: None}
function submitSubratings() {
  let [ids, toDelete, texts, ratings, keybindings] = [[], [], [], [], []];

  subratings.forEach(subrating => {
    ids.push((subrating.toDelete) ? subrating.id + "d" : subrating.id);
    texts.push(subrating.text);
    ratings.push(subrating.rating);
    keybindings.push(subrating.keyBinding);
  });

  $("#srChange").val(1)
  $("#srIds").val(ids.join("___"))
  $("#srTexts").val(texts.join("___"))
  $("#srRatings").val(ratings.join("___"))
  $("#srKeybindings").val(keybindings.join("___"))
}

// Actions

// Read all existing subratings in HTML; that is those generated from FLASK
$(".list-group-item").each(function(index){
  let classes = $(this).attr("class");
  let kb = classes.match(/Keybinding_./);
  kb = (kb) ? kb[0].split("_")[1] : null;
  subratings.push({
    id: $(this).attr("id"), // subrating_XXX
    text: $(this).html(),
    keyBinding: kb,
    rating: colors.indexOf(
      classes.match(/list-group-item-\w+/g)[1].split("-")[3]
    )
  });
  $(this).click(function() {activateSubrating($(this))})
})

// Disable enable add button when text is filled
subrText.change(function() {
  if ($(this).val() === "") {
    addBtn.attr("disabled", true);
  } else {
    addBtn.removeAttr("disabled");
  }
});

// Deactivate other rating buttons and save value
$("#subratingBtnsToolbar .btn").each(function(index) {
  $(this).click(function() { toggleRatings($(this).val()) });
});

// Deactivate other KbMods and save value
kbMods.forEach(btn => btn.click(() => toggleKbMod(btn.val())));

// Send values to subratingsBar
addBtn.click(() => {
  let kb = (kbMod) ? `${kbMod}_${subrKb.val()}` : subrKb.val()
  addSubrating(subrText.val(), subrating, kb, origId, existing)
  subratingChange = true
});

// Activate delete button
delBtn.click(() => deleteSubrating($(`#${origId}`)))
