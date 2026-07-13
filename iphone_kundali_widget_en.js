//====================================================
// Current Transit Kundali Widget
// Small Widget
//====================================================

const BASE_URL = "GIVE_YOUR_API_URL";

Location.setAccuracyToThreeKilometers();

let widget = new ListWidget();
widget.setPadding(0, 0, 0, 0);

try {

  //---------------------------------------
  // Current Location
  //---------------------------------------

  const loc = await Location.current();

  const lat = loc.latitude.toFixed(5);
  const lon = loc.longitude.toFixed(5);

  //---------------------------------------
  // Load Chart Image
  //---------------------------------------

  const req = new Request(
    `${BASE_URL}/api/v1/kundali/chart?lat=${lat}&lon=${lon}&lang=en`
  );

  req.timeoutInterval = 20;

  const image = await req.loadImage();

  //---------------------------------------
  // Widget
  //---------------------------------------

  widget.backgroundColor = Color.white();

  const img = widget.addImage(image);
  img.applyFittingContentMode();


} catch (e) {

  widget.backgroundColor = new Color("#1C1C1E");

  let err = widget.addText("⚠️");
  err.font = Font.boldSystemFont(40);
  err.centerAlignText();

  widget.addSpacer(8);

  let txt = widget.addText("Unable to Load");
  txt.font = Font.mediumSystemFont(12);
  txt.centerAlignText();
  txt.textColor = Color.white();

  widget.addSpacer(4);

  let msg = widget.addText(e.toString());
  msg.font = Font.systemFont(8);
  msg.centerAlignText();
  msg.textColor = Color.lightGray();

}

Script.setWidget(widget);

if (!config.runsInWidget) {
  await widget.presentSmall();
}

Script.complete();