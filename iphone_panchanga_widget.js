//====================================================
// Hora & Panchanga iOS Widget
// Optimized for Medium Widget
//====================================================

const BASE_URL = "http://192.168.31.71:8000";

Location.setAccuracyToThreeKilometers();

let widget = new ListWidget();
widget.setPadding(12, 14, 12, 14);

try {

  //---------------------------------------
  // Current Location
  //---------------------------------------
  const loc = await Location.current();

  const lat = loc.latitude.toFixed(5);
  const lon = loc.longitude.toFixed(5);

  //---------------------------------------
  // API
  //---------------------------------------
  const req = new Request(
    `${BASE_URL}/api/v1/all?lat=${lat}&lon=${lon}`
  );

  req.timeoutInterval = 20;

  const data = await req.loadJSON();

  //---------------------------------------
  // Background
  //---------------------------------------
  widget.backgroundColor = new Color("#1C1C1E");

  //---------------------------------------
  // HEADER
  //---------------------------------------
  let header = widget.addStack();

  let title = header.addText(`${data.hora.symbol} ${data.hora.planet}`);
  title.font = Font.boldSystemFont(22);
  title.textColor = Color.white();

  header.addSpacer();

  let remain = header.addText(data.hora.remaining);
  remain.font = Font.mediumSystemFont(12);
  remain.textColor = Color.lightGray();

  //---------------------------------------
  // Ends / Next
  //---------------------------------------

  widget.addSpacer(2);

  let line = widget.addText(
    `Ends ${data.hora.ends}   •   Next ${data.hora.next}`
  );

  line.font = Font.systemFont(11);
  line.textColor = Color.lightGray();

  widget.addSpacer(6);

  //---------------------------------------
  // Two Columns
  //---------------------------------------

  let row = widget.addStack();
  row.layoutHorizontally();

  //------------------------------------------------
  // LEFT
  //------------------------------------------------

  let left = row.addStack();
  left.layoutVertically();

  let t1 = left.addText("TITHI");
  t1.font = Font.boldSystemFont(10);
  t1.textColor = Color.gray();

  let t2 = left.addText(data.panchanga.tithi);
  t2.font = Font.systemFont(13);
  t2.textColor = Color.white();

  left.addSpacer(5);

  let r1 = left.addText("RAHU");
  r1.font = Font.boldSystemFont(10);
  r1.textColor = Color.gray();

  let r2 = left.addText(data.rahu_kalam);
  r2.font = Font.systemFont(12);
  r2.textColor = Color.white();

  left.addSpacer(4);

  let y1 = left.addText("YAMAGANDA");
  y1.font = Font.boldSystemFont(10);
  y1.textColor = Color.gray();

  let y2 = left.addText(data.yamaganda);
  y2.font = Font.systemFont(12);
  y2.textColor = Color.white();

  //----------------------------------------

  row.addSpacer(24);

  //----------------------------------------
  // RIGHT
  //----------------------------------------

  let right = row.addStack();
  right.layoutVertically();

  let n1 = right.addText("NAKSHATRA");
  n1.font = Font.boldSystemFont(10);
  n1.textColor = Color.gray();

  let n2 = right.addText(data.panchanga.nakshatra);
  n2.font = Font.systemFont(13);
  n2.textColor = Color.white();

  right.addSpacer(5);

  let a1 = right.addText("ABHIJIT");
  a1.font = Font.boldSystemFont(10);
  a1.textColor = Color.gray();

  let a2 = right.addText(data.abhijit);
  a2.font = Font.systemFont(12);
  a2.textColor = Color.white();

  right.addSpacer(4);

  let s1 = right.addText("SUN");
  s1.font = Font.boldSystemFont(10);
  s1.textColor = Color.gray();

  let s2 = right.addText(
    `${data.sunrise} - ${data.sunset}`
  );
  s2.font = Font.systemFont(12);
  s2.textColor = Color.white();

  //---------------------------------------
  // Footer
  //---------------------------------------

  widget.addSpacer();

  let footer = widget.addStack();

  let moon = footer.addText(
    "🌙 " + data.moon.rasi
  );
  moon.font = Font.systemFont(10);
  moon.textColor = Color.lightGray();

  footer.addSpacer();

  let sun = footer.addText(
    "☀️ " + data.sun.rasi
  );
  sun.font = Font.systemFont(10);
  sun.textColor = Color.lightGray();

} catch (e) {

  widget.backgroundColor = new Color("#1C1C1E");

  let err = widget.addText("⚠️ Unable to Load");
  err.font = Font.boldSystemFont(18);
  err.textColor = Color.red();

  widget.addSpacer(8);

  let msg = widget.addText(e.toString());
  msg.font = Font.systemFont(10);
  msg.textColor = Color.lightGray();
}

Script.setWidget(widget);

if (!config.runsInWidget) {
  await widget.presentMedium();
}

Script.complete();