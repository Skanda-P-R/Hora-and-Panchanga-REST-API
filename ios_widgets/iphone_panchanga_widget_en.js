//====================================================
// Hora & Panchanga iOS Widget in English
// Optimized for Medium Widget
//====================================================

const BASE_URL = "GIVE_YOUR_API_URL";

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
  // Three Columns
  //---------------------------------------

  let row = widget.addStack();
  row.layoutHorizontally();

  //------------------------------------------------
  // COLUMN 1: ayana, rutu, masa
  //------------------------------------------------

  let col1 = row.addStack();
  col1.layoutVertically();

  let ay1 = col1.addText("AYANA");
  ay1.font = Font.boldSystemFont(10);
  ay1.textColor = Color.gray();

  let ay2 = col1.addText(data.panchanga.ayana);
  ay2.font = Font.systemFont(12);
  ay2.textColor = Color.white();

  col1.addSpacer(5);

  let ru1 = col1.addText("RUTU");
  ru1.font = Font.boldSystemFont(10);
  ru1.textColor = Color.gray();

  let ru2 = col1.addText(data.panchanga.rutu);
  ru2.font = Font.systemFont(12);
  ru2.textColor = Color.white();

  col1.addSpacer(4);

  let ma1 = col1.addText("MASA");
  ma1.font = Font.boldSystemFont(10);
  ma1.textColor = Color.gray();

  let ma2 = col1.addText(data.panchanga.masa);
  ma2.font = Font.systemFont(12);
  ma2.textColor = Color.white();

  //----------------------------------------

  row.addSpacer(16);

  //----------------------------------------
  // COLUMN 2: tithi, nakshatra, sunrise
  //----------------------------------------

  let col2 = row.addStack();
  col2.layoutVertically();

  let t1 = col2.addText("TITHI");
  t1.font = Font.boldSystemFont(10);
  t1.textColor = Color.gray();

  let t2 = col2.addText(data.panchanga.tithi);
  t2.font = Font.systemFont(12);
  t2.textColor = Color.white();

  col2.addSpacer(5);

  let n1 = col2.addText("NAKSHATRA");
  n1.font = Font.boldSystemFont(10);
  n1.textColor = Color.gray();

  let n2 = col2.addText(data.panchanga.nakshatra);
  n2.font = Font.systemFont(12);
  n2.textColor = Color.white();

  col2.addSpacer(4);

  let s1 = col2.addText("SUNRISE");
  s1.font = Font.boldSystemFont(10);
  s1.textColor = Color.gray();

  let s2 = col2.addText(
    `${data.sunrise} - ${data.sunset}`
  );
  s2.font = Font.systemFont(12);
  s2.textColor = Color.white();

  //----------------------------------------

  row.addSpacer(16);

  //----------------------------------------
  // COLUMN 3: rahu, yamaganda, abhijit
  //----------------------------------------

  let col3 = row.addStack();
  col3.layoutVertically();

  let r1 = col3.addText("RAHU");
  r1.font = Font.boldSystemFont(10);
  r1.textColor = Color.gray();

  let r2 = col3.addText(data.rahu_kalam);
  r2.font = Font.systemFont(12);
  r2.textColor = Color.white();

  col3.addSpacer(5);

  let y1 = col3.addText("YAMAGANDA");
  y1.font = Font.boldSystemFont(10);
  y1.textColor = Color.gray();

  let y2 = col3.addText(data.yamaganda);
  y2.font = Font.systemFont(12);
  y2.textColor = Color.white();

  col3.addSpacer(4);

  let a1 = col3.addText("ABHIJIT");
  a1.font = Font.boldSystemFont(10);
  a1.textColor = Color.gray();

  let a2 = col3.addText(data.abhijit);
  a2.font = Font.systemFont(12);
  a2.textColor = Color.white();

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