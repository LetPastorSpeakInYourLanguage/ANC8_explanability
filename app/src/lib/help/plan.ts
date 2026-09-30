import type { HelpTopic } from "./types";

/** The planning tools: Overview, Map & regions, Scenario planner, Conflict simulator, Your data. */

export const PLAN: HelpTopic[] = [
  {
    key: "overview",
    label: "Overview",
    group: "plan",
    blurb: "The ladder at a glance and four things to act on",
    screen: "/",
    purpose:
      "The front page. It gives the national picture in four numbers and a funnel, points to the four things the data say most need attention, and opens the planning tools.",
    plain: [
      "Think of 100 women who gave birth in the last two years. About 78 saw a health worker for antenatal care at least once (**ANC1+**). About 53 kept going to at least four visits (**ANC4+**). Only about 20 reached the eight visits the WHO recommends (**ANC8+**).",
      "So women are lost at three steps: about 22 never start, 25 start but stop before four, and 33 reach four but stop before eight. The last step is the biggest: of every 100 women who reach four visits, only about 37 go on to eight.",
      "The numbers are counted from the survey itself, weighted so that the women interviewed stand for all women in the country. The green and purple items in **Four things to act on** come from the studio's models and say so.",
    ],
    before: ["basics-ladder"],
    recipes: [
      {
        title: "Brief someone in two minutes",
        steps: [
          "Read the four tiles left to right: most women start antenatal care, half reach four contacts, about one in five reaches eight.",
          "Point at the orange tile: most women who reach four never reach eight. That is the biggest loss.",
          "Click the second of the **Four things to act on** to show the region where the most women get no care at all.",
        ],
      },
    ],
    cards: [
      {
        id: "tiles",
        title: "The four headline numbers",
        shows: "The national share of women reaching each rung, and the share lost between four and eight contacts.",
        read: [
          "**Reach any ANC**: at least one antenatal contact (ANC1+).",
          "**Reach four contacts**: the earlier standard (ANC4+).",
          "**Reach eight contacts**, in red: the WHO recommendation (ANC8+). This is the number the studio is built around.",
          "**Lost between 4 and 8**, in orange: of the women who reached four contacts, the share who never reached eight.",
        ],
        terms: ["rung", "continuation"],
      },
      {
        id: "act-on",
        plain: [
          "Each item is picked by a rule, not by hand. **Orange**: the step of the ladder where the largest share of women is lost. **Red**: the region with the most women a year who get no antenatal care at all (its share with no care times its births). **Green**: of the levers the data support, the one that adds most women reaching eight visits if half the women it applies to were reached. **Purple**: the conflict simulator's estimate for a two-year siege in Amhara.",
        ],
        title: "Four things to act on",
        shows: "Four findings worked out from the studio's own data, each a link to the screen that shows it in detail.",
        read: [
          "**Orange**: where the ladder loses most women. Opens the ANC ladder.",
          "**Red**: the region where the most women each year receive no antenatal care. Opens that region on the map.",
          "**Green**: the lever the data support that moves ANC8+ most, if half the women it applies to were reached. Opens the scenario planner with that lever set.",
          "**Purple**: what a two-year siege in Amhara would cost, from the conflict simulator.",
          "Each is an association or a model estimate, not a promise; the screen it opens says how it was worked out.",
        ],
        tryIt: [{ text: "Open the planner as the green item does", href: "/planner?lv=early:50&rung=anc8" }],
        terms: ["lever", "association"],
      },
      {
        id: "minimap",
        title: "ANC8+ by region",
        shows: "A small map with each region shaded by the share of women reaching eight contacts (24-month cohort). Darker is more.",
        read: [
          "Five shades, from few women to many.",
          "Click a region to open it on the full map, with its analysis.",
        ],
        tryIt: [{ text: "The full map", href: "/map?metric=anc8" }],
      },
      {
        id: "ladder",
        title: "The antenatal care ladder",
        shows: "A funnel: all women, then the share reaching ANC1+, ANC4+ and ANC8+.",
        read: [
          "Each bar is the share of all women with a recent pregnancy who reached that rung.",
          "Between the bars: of the women on the rung above, how many continued and how many were lost.",
          "The widest drop is the step where the most women leave.",
        ],
        terms: ["rung", "continuation"],
      },
      {
        id: "tools",
        title: "Planning tools",
        shows: "Four doors into the working tools: the map, the scenario planner, the conflict simulator and your own data.",
        read: ["Each card says in one line what the tool answers. Click to open it."],
        shot: false,
      },
    ],
  },
  {
    key: "map",
    label: "Map & regions",
    group: "plan",
    blurb: "Where women are lost, and one region's full analysis",
    screen: "/map?region=Somali&metric=never",
    purpose:
      "Shows every region on one measure at a time: how far women get, where they are lost, how many women that is each year, how the region compares with what its circumstances predict, and the circumstances themselves. Clicking a region opens its full analysis beside the map.",
    plain: [
      "Every region's number is what that region's own women told the survey, weighted to stand for all its women. A region rests on a few hundred women, so two regions a point or two apart may differ only by chance; the region panel gives each number's 95% range, and ranges that overlap cannot be told apart.",
      "Shares become women by multiplying by births. About 4.2 million babies are born in Ethiopia each year (UN estimates), so one percentage point of ANC8+ nationally is about 42,000 women a year.",
      "**Against its circumstances.** For each region the studio asks a model how many of its women it would expect to reach the rung, given who they are: their wealth, schooling, age, household, pregnancy history, travel time and so on (the 21 predictors without region and town or countryside). It then compares that with what really happened. Among births in the last two years, Addis Ababa: 69% of women reach eight visits where about 45% would be expected, 24 points better than its circumstances predict. Tigray: 12% where about 20% would be expected, 8 points worse, most likely the war. A region doing better than expected is one to learn from; one doing worse has problems beyond its women's circumstances.",
    ],
    before: ["basics-ladder", "basics-charts"],
    recipes: [
      {
        title: "Find where outreach is most needed",
        steps: [
          "In **Show**, choose **Never start ANC**. Dark regions have the most women with no care at all.",
          "Switch **Show** to **Women with no ANC, per year** to see the same gap counted in women, not shares. A big region with a medium share can hold more women than a small region with a high one.",
          "Click the region at the top of **Regions, ranked** to open its analysis. **What to work on** names its biggest loss and what is needed.",
        ],
      },
      {
        title: "Find a region to learn from",
        steps: [
          "In **Show**, under **Against circumstances**, choose **ANC8+ against its circumstances**.",
          "Green regions do better than their women's wealth, schooling and household profile predict.",
          "Click one: its panel's **What to work on** calls it \"A region to learn from\".",
        ],
      },
      {
        title: "Show the country emptying out",
        steps: ["Press **Play the ladder**. The map steps from ANC1+ to ANC4+ to ANC8+ every couple of seconds. Press **Pause** to stop."],
      },
    ],
    cards: [
      {
        id: "layer",
        title: "Map layer: choosing what to show",
        shows: "The controls that choose the measure every panel on this screen shows.",
        read: [
          "**ANC1+ | ANC4+ | ANC8+**: the three rungs in one click.",
          "**Play the ladder**: steps through the three rungs automatically.",
          "**Show**: every measure, grouped. The ladder; where women are lost; women per year; against circumstances; and the circumstances themselves (for example \"No health insurance\"). Circumstances marked \"a health system can change this\" are the ones programmes can act on.",
          "**Background map**: roads and towns under the regions. Switch it off where there is no internet.",
          "**Values on map**: the number printed on each region.",
        ],
        terms: ["modifiable", "regional-gap"],
      },
      {
        id: "map",
        title: "The map",
        shows: "Each region shaded by the chosen measure. The legend in the corner gives the range for each shade and says what darker means.",
        read: [
          "For the ladder, darker is better (more women reach the rung). For losses and circumstances, darker is worse.",
          "For a gap against circumstances, green is better than expected and red worse.",
          "Click a region to open its analysis; click it again to close it.",
          "The hatched area is contested land with no survey region.",
        ],
        tryIt: [{ text: "Women with no care, per year", href: "/map?metric=never_year" }],
        watch: "Each region rests on a few hundred women. Two regions a shade apart may not really differ: the region panel shows each value's interval.",
      },
      {
        id: "ranked",
        title: "Regions, ranked",
        shows: "The same values as the map, as bars, highest first.",
        read: [
          "The dashed tick is Ethiopia as a whole; the figure after **ETH** in the title is its value.",
          "For gaps the bars are signed: right of centre is better than expected, left worse.",
          "Click a bar to open that region.",
        ],
        terms: ["regional-gap"],
      },
      {
        id: "ladder-maps",
        title: "The ladder, region by region",
        shows: "Three small maps, ANC1+, ANC4+ and ANC8+, all on one fixed 0–100% scale.",
        read: [
          "Because the scale is shared, the three maps compare directly: read left to right and the country empties from reaching care to completing it.",
          "Click a small map to put that rung on the big map; click a region inside one to open it.",
        ],
      },
      {
        id: "heatmap",
        title: "Every region, every measure",
        shows: "A grid: regions down the side, measures across the top, each cell shaded.",
        read: [
          "**Each column is shaded on its own scale**, so compare regions down a column, not cells across a row.",
          "The switch in the title picks the set of measures: **Ladder & losses**, **Circumstances** or **Everything**.",
          "Click a cell to put that measure on the map and open that region. Click a column title to change the map only.",
          "Rows are sorted by the measure on the map.",
        ],
      },
      {
        id: "region",
        title: "A region's analysis",
        shows: "Clicking a region opens a panel beside the map (a full-screen sheet on a phone) with everything the studio knows about it, in the order a planner asks.",
        read: [
          "The coloured tag at the top names its main task. **Outreach** (red): too many women never start. **Early engagement** (orange): women start but stop before four. **Retention** (purple): women reach four and stop before eight.",
          "Under the name: how many women and survey clusters the region's numbers rest on.",
          "The **ANC1+ | ANC4+ | ANC8+** switch changes the rung the sections below talk about.",
          "**Esc** or the × closes it.",
        ],
        tryIt: [{ text: "Open Somali", href: "/map?region=Somali&metric=never" }, { text: "Open Tigray", href: "/map?region=Tigray" }],
        terms: ["cluster"],
      },
      {
        id: "region-far",
        title: "How far women get",
        shows: "The region's own ladder: the share reaching each rung.",
        read: [
          "The grey figures at the right are Ethiopia's values, and under them the region's 95% interval in brackets.",
          "Click a rung to switch the panel to it.",
        ],
        terms: ["ci"],
      },
      {
        id: "region-lost",
        title: "Where women are lost",
        shows: "Two bars, the region and Ethiopia, each split into four groups that add to 100%: never start (red), stop before 4 (orange), stop between 4 and 8 (purple), reach 8 (green).",
        read: [
          "The widest red, orange or purple block is where the region loses most women.",
          "Compare with the Ethiopia bar under it.",
          "Not shown in the ANC-entry cohort, where every woman started.",
        ],
      },
      {
        id: "region-work",
        plain: [
          "**What to work on** reads the region's own ladder. If the biggest block of women is lost before the first visit, the task is outreach (reaching women at all); if between the first and fourth visit, early engagement; if between four and eight, retention (keeping women coming back). The changeable circumstances it lists are the ones pulling the region below Ethiopia in **Why the rung differs**.",
        ],
        title: "What to work on",
        shows: "Plain-language notes on what the region most needs.",
        read: [
          "The first note names the biggest loss, its share of all women, and the kind of work that addresses it.",
          "The second lists the changeable factors pulling the chosen rung down here, with the kind of programme for each.",
          "A green note marks a region doing better than its circumstances predict (one to learn from); a red note, one doing worse (the shortfall is more about services than about the population).",
          "**Try scenarios for …** opens the scenario planner for this region.",
        ],
        terms: ["modifiable", "regional-gap"],
      },
      {
        id: "region-why",
        plain: [
          "The model gives every woman a score made of one part per circumstance, plus a starting value. Average each part over the region's women, and over all women in Ethiopia; the difference, part by part, is exactly the region's difference from Ethiopia. Nothing is left over and nothing is counted twice.",
          "Example: if the region's women are poorer than the average Ethiopian woman, the wealth part pulls its bar to the left; if more of them are insured, the insurance part pushes it right. The longest bars are the circumstances that account for most of the gap.",
          "This is the model's arithmetic: it says which circumstances account for the gap, not that changing them would close it.",
        ],
        title: "Why the rung differs from Ethiopia",
        shows: "Bars that split the difference between the region and the country into groups of circumstances.",
        read: [
          "An additive model predicts each woman's chance as a sum of one part per circumstance, so the region's difference from Ethiopia splits exactly into those parts.",
          "The model is logistic regression, the same one that scores the planner's levers.",
          "Bars to the left pull the region below Ethiopia; to the right, lift it above.",
          "Blue-dotted, darker bars are circumstances a health system can change; faded ones it cannot (wealth, schooling, age).",
          "The figures at the top right: the model's prediction for the region against Ethiopia's.",
        ],
        watch: "This is the model's arithmetic, not proof of cause.",
        terms: ["logistic", "modifiable"],
      },
      {
        id: "region-behind",
        title: "Who is left behind",
        shows: "The chosen rung for groups of women within the region: by wealth, education, residence, whether the pregnancy was wanted, access to a health post, or age at the birth.",
        read: [
          "Pick the grouping with the switch.",
          "The bar is the group's share; the dashed mark is the same group nationally.",
          "Faded bars with an asterisk rest on fewer than 25 women: a direction, not a number.",
        ],
      },
      {
        id: "region-circumstances",
        title: "The region's circumstances",
        shows: "How common each circumstance is among the region's women (dot) against Ethiopia (tick).",
        read: [
          "Blue dots are circumstances a health system can change, listed first; grey ones it cannot.",
          "A dot far right of the tick: much more common here than nationally.",
        ],
        terms: ["modifiable"],
      },
      {
        id: "region-year",
        title: "Women each year",
        shows: "The region's births per year, and how many of those women do not reach eight contacts or receive no care at all.",
        read: ["Births come from UN population estimates; the counts are births times the region's shares. They turn percentages into people to plan for."],
      },
    ],
    faq: [
      { q: "Why is a region grey?", a: "It has no value for the chosen measure in this cohort. ANC1+ and \"never start\" are blank in the ANC-entry cohort, because every woman in it started." },
      { q: "Why don't my region's numbers match the official report?", a: "Switch the cohort to 24 mo, the window the official report uses. The full cohort includes older births." },
    ],
  },
  {
    key: "planner",
    label: "Scenario planner",
    group: "plan",
    blurb: "What changes if programmes reach more women",
    screen: "/planner?lv=insurance:60,intention:50,early:40&rung=anc8",
    purpose:
      "Move sliders for things a health system can change (distance to care, health insurance, wanted pregnancies, an earlier first visit) and see how ANC1+, ANC4+ and ANC8+ would respond in every region, how many more women that is each year, what a budget would buy, and which regions would reach a target.",
    plain: [
      "A **lever** is a change a health system could make, written as a change to women's survey answers. \"Health insurance\" switches uninsured women to insured. The studio then asks the model how likely each woman would be to reach each rung with that answer changed. The average change over all women is the lever's effect. Statisticians call this g-computation.",
      "**Worked example.** 56% of women are uninsured. If every one of them were insured, the model expects ANC1+ to rise by 1.7 points, ANC4+ by 2.9 and ANC8+ by 1.0. The slider says what share of those women a programme reaches: at 50%, the effect is about half of that. With about 4.2 million births a year, one point of ANC8+ is about 42,000 more women a year.",
      "**Levers combine exactly.** Two levers that reach the same woman do not count her twice: every woman has been scored under every combination of the five levers (32 in all), so any mix of slider positions is worked out, not added up.",
      "**Earlier first visit** works differently. It uses a model of the women who started care: how much more likely they are to reach four and eight visits when the first visit comes in the first three months. It cannot change ANC1+, because it applies only to women who already started.",
      "The model is logistic regression on the 21 predictors. It describes the survey, not an experiment: a lever's effect is how differently women with and without that circumstance fare once their other circumstances are the same. That is useful for planning, but it is not proof that a programme would cause the change.",
    ],
    before: ["basics-numbers", "basics-models"],
    recipes: [
      {
        title: "Test one programme",
        steps: [
          "Leave the scope at Ethiopia, or click a region on the map to plan for it alone.",
          "Drag one slider, for example **Health insurance** to 50%: half of uninsured women become insured.",
          "Read the tiles: the rung before and after, and **More women reaching … each year**.",
          "The map and list show where the gain falls.",
        ],
      },
      {
        title: "Spend a budget where it buys most",
        steps: [
          "In **Spend a budget**, type your budget in birr.",
          "Replace the example unit costs with real ones: the cost of reaching one more woman with each lever.",
          "The table lists, region by region and lever by lever, where the money goes and how many more women reach the rung.",
        ],
      },
      {
        title: "See who reaches a target",
        steps: [
          "Set the **Target** slider in **Who reaches a target**, for example 30% ANC8+.",
          "Move levers until more regions' dots cross the dashed line.",
        ],
      },
      {
        title: "Share a scenario",
        steps: ["Copy the address: it holds every slider. Anyone who opens it sees the same scenario, and **Your data** can apply it to a forecast."],
      },
    ],
    cards: [
      {
        id: "tiles",
        plain: [
          "For the scope you chose, every woman is scored twice: as she is, and with the levers at their slider positions. The difference, averaged over the women and weighted to stand for all women, is the change added to the survey's own share. **More women reaching … each year** multiplies each region's change by its births and adds up the regions.",
        ],
        title: "The rungs, now and with the scenario",
        shows: "Three tiles, one per rung, for the current scope (Ethiopia or the chosen region), and a fourth with the women gained each year.",
        read: [
          "The large number is the rung **with** the scenario; under it, **now** and the change in points.",
          "Click a rung's tile to make the map, list and budget about that rung.",
          "**More women reaching … each year** adds up the change across all 14 regions, using each region's births.",
        ],
        terms: ["points"],
      },
      {
        id: "levers",
        plain: [
          "**Supported, or not.** For each lever the planner asks the model: if every woman this lever applies to were reached, would more women reach ANC1+, ANC4+ **and** ANC8+? A lever counts as supported only if the answer is yes for all three rungs. If any rung would fall, however slightly, the lever is marked **not supported for** that rung (for example \"not supported for ANC1+\"), with a line saying why, and it is hidden until you ask to see it.",
          "**Weekly radio health messages** is flagged for ANC1+. Reaching all women who do not listen weekly, the model expects ANC4+ to rise by 3.3 points and ANC8+ by 0.3, but ANC1+ to dip by 0.1. The dip is tiny: almost every woman who can start care already does, so radio cannot add first visits. The strict rule still flags it, so that you decide.",
          "**Women taking part in decisions on their own healthcare** is flagged for ANC1+ and ANC4+. The model expects small falls there (−0.2 and −0.7 points) and a rise at ANC8+ (+0.4). This is a real pattern in the survey: among women with the same wealth, schooling and region, those who say they take part in these decisions are not more likely to make four visits, though they are more likely to make eight. The survey cannot say why.",
          "\"Not supported\" does not mean harmful. It means the survey cannot show the lever would help at every rung.",
        ],
        title: "Levers",
        shows: "One slider per lever: the share of the women it applies to who are actually reached.",
        read: [
          "Under each lever's name: what share of women it applies to here (for example, the share who are uninsured, for insurance).",
          "Under the slider, the lever's **weight** on each rung: the change the model expects if **every** eligible woman were reached, with a small bar and its 95% band. Most move a rung by under a point; the earlier first visit moves ANC8+ by far more.",
          "Sliders combine exactly, not by simple adding: two levers that reach the same women do not double-count.",
          "Logistic regression on the 21 predictors scores the levers; everything on the page follows it.",
          "The circular arrow in the title clears all levers.",
          "**Show the levers the data do not support** adds the levers where the model expects at least one rung to fall; they are there for honesty, marked \"not supported\".",
        ],
        watch: "Association-based: what the model expects if women's circumstances changed, not what a programme would cause.",
        terms: ["lever", "eligible", "g-computation", "association"],
      },
      {
        id: "where",
        title: "Where the scenario moves the rung",
        shows: "A map shaded by the scenario's change on the chosen rung, in points, and a list of regions ranked by women gained per year.",
        read: [
          "Grey regions: no change.",
          "In the list, under each region: its share now → with the scenario. The bar is the change times the region's births, so big regions can top the list with a modest change.",
          "Click a region (map or list) to plan for it alone; the tiles and levers switch to it.",
          "The switch in the title picks the rung.",
        ],
      },
      {
        id: "grid",
        title: "Every region, every rung",
        shows: "The scenario's change for every region on all three rungs, in points, on one shading for the whole grid.",
        read: ["Click a region's row to plan for it; click a rung's column title to switch to it."],
      },
      {
        id: "fixed",
        plain: [
          "The same exact split as **Why the rung differs** on the map, grouped into circumstances a ministry cannot change directly (wealth, schooling, region, culture, household, pregnancy history, work) and circumstances programmes can move (distance to care, insurance, information, wanted pregnancy, women's say in their healthcare).",
          "The bar at the top answers one question: of what holds this region below the country, how much lies in things a programme can change? A small share means most of the gap is in circumstances outside the health system's reach.",
        ],
        title: "What can move and what cannot",
        shows: "What holds a region back, split into circumstances a ministry cannot change directly (left, held fixed in every scenario) and those programmes can move (right, each with its own slider).",
        read: [
          "The bar at the top: of what holds the region below the country (or, for Ethiopia, what separates the regions), the share that is in adjustable circumstances.",
          "Left list (lock icon): wealth, schooling, region, culture, household, history, work. Each bar is that group's part of the gap in approximate points.",
          "Right list: the adjustable groups. Their sliders are the planner's own, so dragging here moves every chart above.",
          "With no region chosen, the bars show how much each group separates the regions on average.",
        ],
        tryIt: [{ text: "What holds Afar back", href: "/planner?region=Afar&rung=anc8" }],
        terms: ["modifiable", "logistic"],
      },
      {
        id: "budget",
        plain: [
          "The budget is spent the way a careful shopper spends: one small purchase at a time (a tenth of one lever's women in one region), always buying next whatever adds the most women reaching the rung per birr, until the money runs out.",
          "Example of the arithmetic: if reaching one woman costs 400 birr, and one in forty women reached goes on to reach eight visits because of it, each extra woman reaching eight costs 16,000 birr. The planner compares that figure across every lever and region and buys the cheapest first.",
        ],
        title: "Spend a budget",
        shows: "Allocates a budget, a tenth of a lever's women at a time, always to the region and lever that buys the most extra women on the chosen rung per birr.",
        read: [
          "Type the **Budget** in birr and a cost per woman reached for each lever.",
          "The two figures: **More women reaching** the rung per year of births, and how much of the budget was **Spent**.",
          "The table lists the purchases, best value first: region, lever, the share of its women reached, the women gained, and the cost per woman gained. Click a row to open that region.",
        ],
        watch: "The costs are placeholders to be replaced with real unit costs. Levers are counted separately, so the total is an upper bound.",
      },
      {
        id: "target",
        plain: [
          "For each region: its share now (ring) and with your levers (dot), against the target line. A region reaches the target when its dot crosses the line. Moving levers shows which regions a programme could bring over it and which stay short, and by how many points.",
        ],
        title: "Who reaches a target",
        shows: "Each region now (ring) and with the scenario (dot), against a target (dashed line).",
        read: [
          "Set the **Target** slider in the title.",
          "At the right: \"reached\", or how many points short the region still is.",
          "A region reaches the target when its dot crosses the line.",
        ],
      },
      {
        id: "gap",
        plain: [
          "The model's expected share for each region comes from its women's circumstances alone: the 21 predictors without region and town or countryside. Actual minus expected is the gap. Among births in the last two years, Addis Ababa reaches eight visits 24 points more often than its women's circumstances predict; Tigray, 8 points less. A big positive gap is a region to learn from; a big negative one points to services, conflict or geography.",
        ],
        title: "Doing better or worse than its circumstances predict",
        shows: "For each region, the share reaching the rung minus what the model predicts from its women's circumstances alone.",
        read: [
          "Right of zero (green): the region does better than its population would suggest: a place to learn from.",
          "Left (red): something about the region itself (services, conflict, geography) holds women back beyond their circumstances.",
          "Under each region: the actual and expected shares.",
        ],
        terms: ["regional-gap"],
      },
      {
        id: "unsupported",
        plain: [
          "These are the levers that fail the planner's rule: the model expects at least one rung to fall if the lever reached every woman it applies to. The numbers in red are the rungs that fall. They stay visible for honesty: a planner may still choose them for other reasons, but the survey cannot show they would help at every rung.",
        ],
        title: "Levers the data do not support",
        shows: "The levers where the chosen model expects at least one rung to fall, not rise, when applied, with every lever model's estimates.",
        read: [
          "Each cell: the change at full reach from logistic regression.",
          "These do not show the programmes would harm. They show the survey cannot show they would help: women who listen to the radio weekly, for example, are no more likely to complete care once everything else about them is known.",
        ],
        terms: ["association", "logistic"],
      },
    ],
    faq: [
      { q: "Why does the earlier first visit not move ANC1+?", a: "It only applies to women who already started care, so it cannot change whether they start." },
      { q: "Can I trust the size of a lever's effect?", a: "Treat it as the size of an association. The bands show how it varies with who lives where, not the uncertainty of the model itself, and not what a programme would really achieve." },
    ],
  },
  {
    key: "war",
    label: "Conflict simulator",
    group: "plan",
    blurb: "What a war like Tigray's would do elsewhere",
    screen: "/war?hit=Amhara&rung=anc1",
    purpose:
      "Built from what the Tigray war did to antenatal care, and checked against Amhara, which the model never saw. Choose regions, how long fighting lasts, how intense it is and what happens after a ceasefire, then watch the effect arrive, peak and fade quarter by quarter.",
    plain: [
      "The simulator learned from one real event, the Tigray war. It compares Tigray's births during and after the war with births over the same months in regions without major conflict, so anything that changed across the whole country at the same time cancels out.",
      "**What the war did.** For a pregnancy spent entirely under the conflict, the odds of even one antenatal visit fell to about one seventh of normal, and the odds of four visits to under half. The effect on eight visits is too uncertain to call, because eight visits were already rare in Tigray. Counted in the survey, the war cut first visits by about 13 points and four visits by about 14. The simulator's model reproduces about 11 to 12 points of each.",
      "**Moving it elsewhere.** The simulator applies the same drop to another region's own levels, for the quarters you choose, scaled by **Intensity** (1× is Tigray). After a ceasefire, services come back gradually. The Tigray data fit a recovery anywhere from immediate to four years about equally well, 12 months fitting best, which is why recovery time is a setting.",
      "**Siege or insurgency.** A siege cuts services until the fighting stops, as in Tigray. An insurgency hits as hard at the start but services adapt within months. Amhara, which the model never saw, is the check: its insurgency looked like the siege for the first half-year and then far milder.",
    ],
    before: ["basics-numbers", "basics-charts"],
    recipes: [
      {
        title: "Run a scenario",
        steps: [
          "Pick a **Pattern**: Siege (services cut until a ceasefire) or Insurgency (services adapt while fighting goes on).",
          "Click regions to put them in conflict (red chips, or click the map).",
          "Set **Fighting lasts** and **Intensity** (1× is the Tigray war).",
          "Choose whether services return after the ceasefire, and how fast.",
          "Press **Play** under the map to watch it unfold.",
        ],
      },
      {
        title: "Check whether to trust it",
        steps: [
          "Read **Does the model reproduce Tigray?**: the model's dots should sit inside the survey's intervals.",
          "Read **Checking on Amhara**: how the siege and insurgency patterns compare with what happened in a region the model never saw.",
        ],
      },
    ],
    cards: [
      {
        id: "tiles",
        title: "The cost in women",
        shows: "Over six years, across the regions in conflict: more women with no antenatal care at all, fewer reaching ANC4+ and ANC8+, and how long the focus region takes to recover.",
        read: [
          "Each count has its 95% band underneath (\"none\" at the low end means the band includes no loss).",
          "Click a rung's tile to put it on the map and charts.",
          "**Back to normal**: quarters after the ceasefire until every rung is within one point of its usual level; \"never\" if services are not restored.",
        ],
        terms: ["ci"],
      },
      {
        id: "scenario",
        title: "Scenario",
        shows: "The settings of the conflict.",
        read: [
          "**Pattern**. Siege · Tigray: services cut until a ceasefire. Insurgency · Amhara: the same shock at onset, then services adapt within a few months while fighting continues.",
          "**Regions in conflict**: click to add or remove (red means in).",
          "**Fighting lasts**: in quarters of a year; the Tigray war lasted eight.",
          "**Intensity**: 1× reproduces Tigray; 0× is no effect; 1.5× is worse than Tigray.",
          "**After the ceasefire**: services return, or stay down.",
          "**Recovery time**: how many months services take to come back. The Tigray data fit a wide range about equally well; \"·fit\" marks the best fit.",
          "The circular arrow in the title resets everything.",
        ],
        terms: ["siege"],
      },
      {
        id: "map",
        title: "Map and timeline",
        shows: "Each region in conflict shaded by how many points of women it loses on the chosen rung in the quarter shown. Grey regions are not in the scenario.",
        read: [
          "The timeline under the map runs over six years (Y1 Q1 to Y6 Q4). The red span is the fighting.",
          "Press **Play** to animate, or drag the slider to a quarter. The tag at the right says before, fighting or after.",
          "The legend: points lost this quarter, from under 1 to 10 or more.",
          "Click a region to add or remove it.",
        ],
      },
      {
        id: "trajectory",
        title: "The ladder through the conflict",
        shows: "For the focus region: the share reaching each rung by quarter of birth, with its band.",
        read: [
          "Dashed lines: the region's level without conflict.",
          "The lightly shaded span is the fighting; the vertical line is the quarter on the map.",
          "With several regions in conflict, the switch in the title picks which to follow.",
          "Hover for each rung's value and its drop in points.",
        ],
      },
      {
        id: "breaks",
        title: "Which rung breaks first",
        shows: "The deepest drop on each rung during the scenario: the level without conflict (ring) and at the worst quarter (red dot).",
        read: [
          "At the right: the drop in points. Underneath: when it peaks, and the drop as a share of the rung's own level.",
          "In Tigray the war mostly stopped women starting care and reaching four contacts; eight contacts were already rare, so there was less to lose.",
        ],
      },
      {
        id: "tigray",
        title: "What happened in Tigray",
        shows: "The survey itself: the share of Tigray women reaching the rung by half-year of the birth.",
        read: [
          "Red dots with a band: what the survey found, with 95% intervals.",
          "Solid line: the model. Dashed: the model with the war switched off. Dotted: regions without conflict.",
          "The war ended in November 2022; births from mid-2023 were conceived in peace.",
          "Pick the rung with the switch.",
        ],
      },
      {
        id: "amhara",
        title: "Checking on Amhara",
        shows: "A test on a region the model never saw: from August 2023 the Fano insurgency put Amhara pregnancies under conflict.",
        read: [
          "Red dots: what happened. Orange: the full Tigray-style siege. Green: services that adapt. Dashed: no conflict.",
          "The siege line predicts the first half-year well, then a far deeper collapse than happened.",
          "The adapting line's adaptation time is fitted to Amhara, so it describes Amhara rather than testing the model on it.",
        ],
        watch: "A siege and an insurgency are different disruptions, which is why the simulator offers both.",
      },
      {
        id: "reproduce",
        title: "Does the model reproduce Tigray?",
        shows: "The simulator's model on Tigray at intensity 1 (dots) against the war's effect measured directly from the survey (rings, with intervals).",
        read: [
          "The survey estimate is a difference-in-differences: Tigray's change from wartime to post-war births, minus the change in regions without conflict.",
          "Dots inside the rings' intervals: the model reproduces what the survey shows.",
        ],
        watch: "Women displaced out of Tigray, and clusters not surveyed for security, are missing, so the real effect is more likely larger than shown. Moving it to another region assumes the same kind of disruption.",
        terms: ["did", "bootstrap"],
      },
    ],
  },
  {
    key: "data",
    label: "Your data",
    group: "plan",
    blurb: "Trends and forecasts from your own ANC counts",
    screen: "/your-data",
    purpose:
      "Load your own monthly or quarterly ANC counts (a DHIS2 export works) and see the trend, a forecast tested on your own series, seasonal patterns, and what the scenario planner's levers would add. Nothing leaves your computer.",
    plain: [
      "A forecast is only as good as the method's past record on your own numbers, so the studio tests before it trusts. It tries six simple forecasters: the last value, the same season last year, a moving average, a straight trend, a smoothed trend, and a trend with seasons.",
      "For each, it pretends to stand at an earlier point in your series, forecasts the next periods, and checks against what really happened. It repeats this moving forward one period at a time. The forecaster with the smallest average miss makes the forecast, and the shaded bands are built from its real misses on your series: the dark band holds 80% of them, the light band 95%.",
      "When a very simple forecaster wins, your series has little pattern beyond noise, and that is worth knowing too. The green line adds the scenario planner's levers as extra coverage, growing to their full effect over a year.",
    ],
    before: ["basics-charts"],
    recipes: [
      {
        title: "Forecast your facilities",
        steps: [
          "Click **Template** to download an example file, and fill it in (or export from DHIS2 with the same columns).",
          "Click **Load a CSV** and choose your file.",
          "Pick the **Measure** (ANC1+, ANC4+ or ANC8+), and **Coverage** if your file has expected pregnancies.",
          "Choose a facility in the unit list, or leave all units together.",
          "Pick how far ahead to forecast.",
        ],
      },
      {
        title: "Add a programme to the forecast",
        steps: [
          "Set levers in the **Scenario planner** first.",
          "Come back: the green line adds their expected effect, growing to full size over a year.",
        ],
      },
    ],
    cards: [
      {
        id: "mode",
        title: "What to load",
        shows: "The switch at the top chooses between two tools.",
        read: [
          "**Monthly or quarterly ANC counts**: the trend and forecast tool described on this page.",
          "**A register of women (first-visit screen)**: the First-visit screener, which has its own Help topic.",
          "The green shield: files are read in this browser and never uploaded.",
        ],
        tryIt: [{ text: "The first-visit screener", href: "/your-data?mode=register" }],
      },
      {
        id: "source",
        title: "Data",
        shows: "Where the numbers come from: a sample or your own file.",
        read: [
          "**Sample: synthetic woreda**: a made-up woreda of six facilities over four years, shaped like a DHIS2 export, for trying the tools. Not data.",
          "**Sample: survey regions**: each region's share reaching each rung by quarter of birth, from the survey. Real but noisy: 30–70 women per region and quarter.",
          "**Load a CSV**: your file. **Template**: an example with the right columns.",
          "Columns: **period** (2023-01 or 2023Q1), **org_unit** (facility or area), **expected_pregnancies** (optional), **anc1**, **anc4**, **anc8**. Other names for the same things are recognised.",
          "Any problems with the file are listed in orange under the buttons.",
        ],
      },
      {
        id: "tiles",
        title: "Latest, change, forecast, forecaster",
        shows: "Four tiles that sum up the series.",
        read: [
          "**Latest**: the last period's value.",
          "**Against a year earlier**: the change from the same period a year before (green up, red down).",
          "**Forecast**: the value at the end of the forecast, with its 80% range.",
          "**Forecaster chosen**: the method that made the smallest errors on your series.",
        ],
        terms: ["forecast"],
      },
      {
        id: "trend",
        title: "Trend and forecast",
        shows: "Your data (solid line) and the forecast (dashed) with its 80% and 95% bands.",
        read: [
          "**Measure**: ANC1+, ANC4+ or ANC8+. **Count | Coverage**: numbers of women, or the share of expected pregnancies (only if the file has them).",
          "The unit list picks one facility or area. **Horizon**: how far ahead.",
          "The dark band holds the next values 80% of the time, the light band 95%. Both are built from the forecaster's real misses on your own series.",
          "The green line adds the scenario planner's levers, reaching full effect over a year. Untick **Apply the scenario planner's levers** to hide it.",
          "Hover for any period's values.",
        ],
        terms: ["forecast", "backtest"],
      },
      {
        id: "forecasters",
        title: "How each forecaster did on this series",
        shows: "Every forecasting method tried, ranked by its average miss when tested on your own series.",
        read: [
          "Each method was fitted on the start of the series and asked to forecast the next periods, over and over, moving forward one period at a time.",
          "The shortest bar (blue) is used for the forecast.",
          "When a simple method wins, the series has little pattern to learn.",
        ],
        terms: ["backtest"],
      },
      {
        id: "season",
        title: "By season",
        shows: "How much each calendar month runs above or below the year around it, averaged over the years in the file.",
        read: [
          "Blue bars: busier months; red: quieter.",
          "Needs at least two years of monthly data.",
          "In the synthetic sample the dip is the main rains, June to September, when roads close.",
        ],
        terms: ["seasonality"],
      },
    ],
  },
];
