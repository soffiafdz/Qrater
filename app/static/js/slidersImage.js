// Changes
let filtersApplied = false;

// Toggle Offcanvas
$("#toggleSliders").click(function(e) {
  if (!filtersApplied) {
  document.getElementById("sliderBrightness").value = 1;
  document.getElementById("sliderContrast").value = 1;
  document.getElementById("sliderSaturation").value = 1;
  };
  let myOffcanvas = $("#offcanvasSliders")[0];
  let bsOffcanvas = new bootstrap.Offcanvas(myOffcanvas);
  e.stopPropagation();
  bsOffcanvas.toggle();
});

// Sliders to change Brightness/Contrast/Saturation
// Brightness
$("#sliderBrightness").change(function(){
  $("#img").css("filter", `brightness(${$(this).val()})`);
  filtersApplied = true
  resetButton.removeAttr("disabled")
});

// Contrast
$("#sliderContrast").change(function(){
  $("#img").css("filter", `contrast(${$(this).val()})`);
  filtersApplied = true
  resetButton.removeAttr("disabled")
});

// Saturation
$("#sliderSaturation").change(function(){
  $("#img").css("filter", `saturate(${$(this).val()})`);
  filtersApplied = true
  resetButton.removeAttr("disabled")
});

//Reset Button
let resetButton = $("#resetSliderBtn")

//Restart
$("#resetSliderBtn").click(function() {
  document.getElementById("sliderBrightness").value = 1;
  $("#img").css("filter", "brightness(1)");
  document.getElementById("sliderContrast").value = 1;
  $("#img").css("filter", "contrast(1)");
  document.getElementById("sliderSaturation").value = 1;
  $("#img").css("filter", "saturate(1)");
  filtersApplied = false;
  resetButton.attr("disabled", true);
});
