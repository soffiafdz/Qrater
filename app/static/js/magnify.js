// $("#zoomButton")
$("#zoomButton").click(() => {
  if ($(".img-magnifier-glass").length) {
    $(".img-magnifier-glass").remove();
  } else {
    zoom = 2; magnify("img", zoom);
  };
});

/* <svg version="1.1" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="612px" height="612px" viewBox="0 0 612 612" style="enable-background:new 0 0 612 612;" xml:space="preserve"> */

function magnify(imgID, zoom) {
  var img, glass, w, h, bw;
  img = document.getElementById(imgID);

  /* Create magnifier glass: */
  glass = document.createElement("DIV");
  glass.setAttribute("class", "img-magnifier-glass");

  /* Add little crosshair */
  const crosshair = document.createElement("DIV");
  const crosshairSvg = document.createElementNS(
    "http://www.w3.org/2000/svg", "svg"
  )
  const crosshairPath = document.createElementNS(
    'http://www.w3.org/2000/svg', 'path'
  )

  crosshairSvg.setAttribute('width', '24px');
  crosshairSvg.setAttribute('height', '24px');
  crosshairSvg.setAttribute('viewBox', '0 0 24 24');
  crosshairSvg.setAttribute('style', 'enable-background:new 0 0 24 24;');
  crosshairSvg.setAttribute('xml:space', 'preserve');
  crosshairPath.setAttribute(
    'd',
    'M587.572,186.882c-16.204-37.755-37.897-70.185-65.252-97.375c-27.183-27.019-59.955-48.705-97.702-64.909 C386.742,8.344,347.324,0.171,305.836,0.171c-41.496,0-80.914,8.173-118.79,24.427c-37.748,16.204-70.349,37.727-97.703,64.909 c-27.19,27.026-48.998,59.498-65.252,97.375C7.895,224.629,0,264.176,0,305.664c0,41.495,7.895,81.37,24.092,119.124 c16.254,37.869,38.147,70.264,65.252,97.367c27.44,27.441,59.955,49.049,97.703,65.252c37.876,16.254,77.294,24.422,118.79,24.422 h0.664c41.495,0,80.913-8.168,118.789-24.422c37.748-16.203,70.185-37.896,97.367-65.252 c27.019-27.189,48.712-59.619,64.916-97.367C603.826,386.913,612,347.159,612,305.664C612,264.176,603.826,224.75,587.572,186.882z M486.521,324.067h87.667c-3.013,43.836-15.727,84.66-38.483,121.801c-22.75,37.141-52.603,66.793-89.672,89.672 c-37.22,22.965-77.294,35.807-121.131,38.812v-87.666c0-10.373-8.694-18.738-19.066-18.738c-9.708,0-18.738,8.365-18.738,18.738 v87.666c-43.837-3.006-83.912-15.848-121.131-38.812c-37.069-22.879-66.922-52.531-89.672-89.672 c-22.757-37.141-35.471-77.965-38.483-121.801h87.666c10.372,0,18.403-8.031,18.403-18.403c0-9.701-8.031-18.403-18.403-18.403 H37.812c3.012-43.83,15.726-83.982,38.483-121.124c22.75-37.141,52.603-66.801,89.672-89.679 c37.219-22.964,77.294-35.799,121.131-38.812v87.667c0,10.372,9.03,18.738,18.738,18.738c10.372,0,19.066-8.366,19.066-18.738 V37.647c43.837,3.013,83.911,15.848,121.131,38.812c37.069,22.878,66.922,52.538,89.672,89.679 c22.757,37.141,35.471,77.294,38.483,121.124h-87.667c-10.372,0-18.402,8.702-18.402,18.403 C468.119,316.036,476.15,324.067,486.521,324.067z'
  );

  crosshairSvg.appendChild(crosshairPath)
  crosshair.appendChild(crosshairSvg)
  glass.appendChild(crosshair)

  /* Insert magnifier glass: */
  img.parentElement.insertBefore(glass, img);

  /* Set background properties for the magnifier glass: */
  glass.style.backgroundImage = "url('" + img.src + "')";
  glass.style.backgroundRepeat = "no-repeat";
  glass.style.backgroundSize = (img.width * zoom) + "px " + (img.height * zoom) + "px";
  glass.style.zIndex = "1";
  if (filtersApplied) glass.style.filter = $("#img").css("filter");
  bw = 3;
  w = glass.offsetWidth / 2;
  h = glass.offsetHeight / 2;

  /* Execute a function when someone moves the magnifier glass over the image: */
  glass.addEventListener("mousemove", moveMagnifier);
  img.addEventListener("mousemove", moveMagnifier);

  /*and also for touch screens:*/
  glass.addEventListener("touchmove", moveMagnifier);
  img.addEventListener("touchmove", moveMagnifier);
  function moveMagnifier(e) {
    var pos, x, y;
    /* Prevent any other actions that may occur when moving over the image */
    e.preventDefault();
    /* Get the cursor's x and y positions: */
    pos = getCursorPos(e);
    x = pos.x;
    y = pos.y;
    /* Prevent the magnifier glass from being positioned outside the image: */
    if (x > img.width - (w / zoom)) {x = img.width - (w / zoom);}
    if (x < w / zoom) {x = w / zoom;}
    if (y > img.height - (h / zoom)) {y = img.height - (h / zoom);}
    if (y < h / zoom) {y = h / zoom;}
    /* Set the position of the magnifier glass: */
    glass.style.left = (x - w) + "px";
    glass.style.top = (y - h) + "px";
    /* Display what the magnifier glass "sees": */
    glass.style.backgroundPosition = "-" + ((x * zoom) - w + bw) + "px -" + ((y * zoom) - h + bw) + "px";
  }

  function getCursorPos(e) {
    var a, x = 0, y = 0;
    e = e || window.event;
    /* Get the x and y positions of the image: */
    a = img.getBoundingClientRect();
    /* Calculate the cursor's x and y coordinates, relative to the image: */
    x = e.pageX - a.left;
    y = e.pageY - a.top;
    /* Consider any page scrolling: */
    x = x - window.pageXOffset;
    y = y - window.pageYOffset;
    return {x : x, y : y};
  }
}
