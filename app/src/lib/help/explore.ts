import type { HelpTopic } from "./types";

/** The exploratory analysis: the ladder, predictor selection, models compared, cohorts. */

export const EXPLORE: HelpTopic[] = [
  {
    key: "ladder",
    label: "The ANC ladder (screen)",
    group: "explore",
    blurb: "Who reaches each rung, and where they stop",
    screen: "/explore/ladder",
    purpose:
      "The ladder in depth: the full spread of contact counts behind the three rungs, which groups of women climb further, which regions keep women and which lose them, and which circumstances matter more the higher up the ladder a woman goes.",
    before: ["basics-ladder", "basics-charts"],
    recipes: [
      {
        title: "See one region's ladder",
        steps: [
          "Pick a region (on the map, or with the finder). Every chart here switches to it, with Ethiopia as a dashed line for comparison.",
          "Read **How many contacts women had**: where the bars bunch tells you where women stop.",
        ],
      },
      {
        title: "Find who is left behind",
        steps: ["In **The ladder, group by group**, pick **Wealth**, then **Education**. The longer a row's line, the more of that group is lost on the way up."],
      },
    ],
    cards: [
      {
        id: "tiles",
        title: "The rungs, with intervals",
        shows: "The share reaching each rung for the current scope and cohort, with its 95% interval, and the share lost between four and eight contacts.",
        read: [
          "Click a rung's tile to choose which rung's value is printed at the right of **The ladder, group by group**.",
          "The interval says how precisely the survey pins the value down.",
        ],
        terms: ["ci", "continuation"],
      },
      {
        id: "contacts",
        title: "How many contacts women had",
        shows: "The share of women with each number of antenatal contacts, from 0 to 12 or more.",
        read: [
          "The colours are the rungs: red is no care, then ANC1+ (1–3), ANC4+ (4–7) and ANC8+ (8 or more).",
          "The three rungs are just cuts through this one spread.",
          "Look for the peaks at three to four contacts and at eight.",
          "With a region chosen, the dashed line is Ethiopia. The tag says the cohort and how many women.",
        ],
      },
      {
        id: "survival",
        title: "Still in care after each contact",
        shows: "The share of all women who had at least that many contacts. The curve steps down wherever women leave.",
        read: [
          "The first steep step is women who never start.",
          "The drop after four is the loss the eight-contact standard exposes.",
          "Dashed vertical lines mark the three rungs; hover for exact shares.",
        ],
      },
      {
        id: "groups",
        title: "The ladder, group by group",
        shows: "One row per group of women (for example each wealth fifth), with three dots: the share reaching ANC1+, ANC4+ and ANC8+.",
        read: [
          "The longer the line from the first dot to the last, the more of that group is lost on the way up.",
          "Pick the grouping with the switch (a list on a phone).",
          "Faded rows rest on fewer than 25 women.",
        ],
      },
      {
        id: "regions",
        title: "Where each region keeps and loses women",
        shows: "A grid of regions against four steps: starting care, continuing from 1 to 4 contacts, continuing from 4 to 8, and reaching eight.",
        read: [
          "Each column is shaded on its own: darker is better on that step. Compare regions down a column.",
          "A region dark on **Start** but light on **Continue 4→8** gets women in but does not keep them.",
          "Click a region to follow it through the page.",
        ],
        terms: ["continuation"],
      },
      {
        id: "predictable",
        title: "How predictable each rung is",
        shows: "For each rung: what guessing gives (ring, the share who reach it) and the best model's average precision on the held-out women (dot).",
        read: [
          "The distance between ring and dot is what the predictors add.",
          "ANC8+ is the hardest rung to predict, but the one where prediction adds most relative to chance.",
          "The model's name and its AUROC are shown with each rung.",
        ],
        terms: ["ap", "auroc", "chance", "heldout"],
      },
      {
        id: "domains",
        title: "What matters at each rung",
        shows: "One line per group of predictors (access and distance, wealth, education, reproductive history and so on): its share of what the model uses at each rung.",
        read: [
          "A line that rises from ANC1+ to ANC8+ matters more for going further up the ladder.",
          "Hover a name in the key to pick its line out.",
          "**Measured by**: each library model's own account on the full candidate pool (logistic regression and explainable boosting split their predictions exactly; random forest and XGBoost by SHAP), or the accuracy lost when the group is removed (Drop-one). Where they agree, the finding is solid.",
        ],
        terms: ["logistic", "ebm", "shap", "drop-one"],
      },
      {
        id: "patterns",
        title: "Predictors that open the door, and predictors that keep women coming",
        shows: "Two lists: predictors that matter most for starting care at all (left), and those that matter more the further up the ladder a woman goes (right).",
        read: [
          "The bar is how much the predictor's share of the model shifts from ANC1+ to ANC8+.",
          "Under each: its group, and how many of three explanation methods agree.",
          "Left-side predictors point to access problems; right-side ones to what keeps women coming back.",
        ],
        watch: "These are associations: a predictor that matters further up is where women who stay differ from women who stop.",
        terms: ["association"],
      },
    ],
  },
  {
    key: "predictors",
    label: "Predictor selection",
    group: "explore",
    blurb: "From 6,648 survey columns to the few that predict",
    screen: "/explore/predictors?rung=anc8",
    purpose:
      "How the study went from every question in the survey to the handful of answers that carry the prediction, and how sure it is. It matters for planning because a short set means fewer questions to ask a woman at her first visit.",
    before: ["basics-models", "basics-charts"],
    recipes: [
      {
        title: "Answer: how many questions do we really need?",
        steps: [
          "Pick the rung (ANC8+ is the one the study is about).",
          "In **How many predictors does it need?**, follow the solid line: most of the accuracy arrives with the first two or three predictors.",
          "In **Tested on the held-out women**, check that the small set holds up on women nothing had seen.",
        ],
      },
    ],
    cards: [
      {
        id: "tiles",
        title: "From columns to a few",
        shows: "Five counts: every column in the survey, those answered by enough women, those tested for selection, those that clear the bar at this rung, and the strongest few (named).",
        read: ["The last tile names the strongest predictors for the chosen rung."],
        terms: ["predictor", "tier"],
      },
      {
        id: "funnel",
        title: "From 6,648 survey columns to a handful",
        shows: "How many variables were left after each step, from the whole questionnaire to the strongest few.",
        read: [
          "On a log scale, so the small sets stay visible next to 6,648.",
          "Each step's grey line says what was removed and why: not asked in this survey round, empty, administrative, measured at or after the birth, answered by fewer than half the women, or not known before care starts.",
          "The last two steps depend on the rung chosen in the title.",
          "The note underneath: how many near-copies (two codings of the same thing) were removed, and that removing them barely changed accuracy.",
        ],
        terms: ["screening"],
      },
      {
        id: "how-many",
        title: "How many predictors does the rung need?",
        shows: "Accuracy (average precision on the development women) against the number of predictors, on a log scale.",
        read: [
          "**Solid line**: build a set from nothing, best predictor first.",
          "**Dashed**: the same, but only within the 21-predictor set.",
          "**Dotted**: add the other predictors to the 21 one at a time.",
          "**Big dots**: the named sets (Top 2, Top 4, the 21, all of them).",
          "The dashed horizontal line is chance. Where the curve flattens, more predictors add little.",
          "Hover a point for the predictor added at that step.",
        ],
        terms: ["forward-selection", "ap", "cv"],
      },
      {
        id: "add-one",
        title: "Adding one predictor to the 21",
        shows: "For the 15 best candidates: the accuracy gained by adding each one to the 21, averaged over five resamples, with the range across them.",
        read: [
          "The dashed line is the bar: +0.005 average precision in most resamples.",
          "Faded rows do not clear it.",
        ],
        terms: ["add-one", "tier"],
      },
      {
        id: "drop-one",
        title: "Taking one out of the 21",
        shows: "How much accuracy the 21 lose when each one is removed.",
        read: [
          "Bars to the right (blue): the predictor carries information the others do not.",
          "Bars to the left (grey): the set does as well or better without it.",
          "The tag says how many of the 21 contribute.",
        ],
        terms: ["drop-one"],
      },
      {
        id: "heldout",
        title: "Tested on the held-out women",
        shows: "Average precision of each predictor set on the 1,375 women the selection never saw, under four kinds of model.",
        read: [
          "Each row a set (from the strongest few to all of them), each colour a model family.",
          "The dashed line is chance.",
          "A small set that matches a large one is the practical win: fewer questions to ask.",
        ],
        terms: ["heldout", "chance"],
      },
      {
        id: "frequency",
        title: "How often each predictor is picked",
        shows: "Selection was repeated many times on resampled development women; the bar is the share of repeats that picked each predictor.",
        read: [
          "Green: among the strongest few. Blue: the next tier.",
          "Picked every time is a stable finding; picked half the time is a coin toss.",
          "Run for ANC8+ only; switch the rung to ANC8+ if the panel is empty.",
        ],
        terms: ["selection-frequency"],
      },
      {
        id: "matrix",
        title: "Every predictor at every rung",
        shows: "The 24 predictors that matter most at the chosen rung (rows) against the three rungs (columns).",
        read: [
          "One shading for the whole grid, so any two cells compare.",
          "A row that darkens to the right matters more for going further up the ladder.",
          "**Measure**: a library model's share of what it uses on the full candidate pool (exact for logistic regression and explainable boosting, by SHAP for random forest and XGBoost), or the accuracy the predictor adds to the 21.",
          "Click a column title to switch rung.",
        ],
        terms: ["logistic", "ebm", "shap"],
      },
      {
        id: "pool",
        title: "Does a bigger pool help?",
        shows: "The same model trained twenty times with different random starts, on the 21 predictors (rings) and on the full pool (dots).",
        read: [
          "Under each rung: how many of the twenty runs favoured the bigger pool.",
          "At the right: the average difference. A small difference means the 21 already carry most of what the pool knows.",
          "Click a rung to switch to it.",
        ],
      },
      {
        id: "too-good",
        title: "Columns that looked too good",
        shows: "The survey columns with the strongest raw link to ANC8+, and why each was excluded before any model saw it.",
        read: [
          "Nearly all were asked of only a few women, so a near-perfect score is an accident of small numbers.",
          "Others were measured during or after the care itself, so they would \"predict\" the outcome by already knowing it.",
        ],
        terms: ["screening"],
      },
    ],
  },
  {
    key: "models",
    label: "Models compared",
    group: "explore",
    blurb: "Every model, every rung, every predictor set",
    screen: "/explore/models?rung=anc8",
    purpose:
      "Every model the study built, side by side and honestly: on the development women that tuning saw, and on the held-out women nothing saw. It also shows what tuning bought, whether the probabilities can be trusted, and whether a model is worth acting on. For one model in depth, use Model analysis.",
    before: ["basics-models", "basics-charts"],
    recipes: [
      {
        title: "Pick a model you can trust",
        steps: [
          "In **Every model, development against held-out**, rank by the dots (held-out), not the rings.",
          "In **Are the probabilities honest?**, prefer a model whose dots hug the diagonal.",
          "In **Is the model worth acting on?**, check its line sits above both \"act on everyone\" and \"act on no one\" at the risk you would act at.",
        ],
      },
    ],
    cards: [
      {
        id: "set",
        title: "Choosing the predictor set",
        shows: "Every model was trained on four predictor sets, and a switch picks which one the screen shows.",
        read: [
          "**Full pool**: every candidate predictor known before antenatal care starts.",
          "**21 set**: the 21-predictor set.",
          "**Short set**: the strongest few predictors, those that clear the bar at the rung.",
          "**Parsimonious**: a small set chosen to keep most of the accuracy with far fewer questions.",
          "Comparing the same model across sets shows what the extra questions buy. If a short set scores close to the full pool, it is the cheaper tool.",
        ],
        terms: ["predictor", "tier"],
        shot: false,
      },
      {
        id: "tiles",
        title: "Best on held-out women",
        shows: "For each rung, the best model's average precision on the held-out women, and chance for comparison.",
        read: ["Click a rung's tile to switch the page to it."],
        terms: ["ap", "heldout", "chance"],
      },
      {
        id: "dev-held",
        title: "Every model, development against held-out",
        shows: "Each model's accuracy on the development women (ring) and on the held-out women (dot).",
        read: [
          "A long line from ring to dot is optimism: the model looked better during building than it is.",
          "Rank models by the dots.",
          "Networks are orange and tagged. Every row is on the predictor set chosen above.",
          "The dashed line is chance. The note underneath says whether held-out accuracy fell or rose overall.",
        ],
        terms: ["optimism", "cv", "heldout"],
      },
      {
        id: "by-rung",
        title: "Model by rung",
        shows: "Held-out scores for every model at every rung.",
        read: [
          "Each column is shaded on its own (rungs differ in difficulty): read a column from dark to light for the ranking at that rung.",
          "**Measure**: average precision, the gain over chance, AUROC, or the Brier score (for Brier, lower is better).",
          "Every model is on the predictor set chosen above.",
        ],
        terms: ["ap", "lift", "auroc", "brier"],
      },
      {
        id: "by-set",
        title: "Model by predictor set",
        shows: "Held-out average precision for every model on each of the four predictor sets, at this rung. The number of predictors is in each column title.",
        read: [
          "One shading for the whole grid, so any two cells compare.",
          "A small set that holds its colour is the cheaper tool: fewer questions for the same accuracy.",
          "Click a column to show that set on the rest of the page.",
        ],
      },
      {
        id: "tuning",
        title: "Does tuning pay?",
        shows: "Each model with its default settings (ring) and after tuning (dot), on the development women and the full candidate pool.",
        read: ["Most gains are small: the models are close before and after tuning."],
        terms: ["tuning"],
      },
      {
        id: "settings",
        title: "Which settings matter",
        shows: "For the chosen model, each tuned setting moved one step down and one step up while the others stay fixed (development women, full candidate pool).",
        read: [
          "Red dot: the worse of the two neighbours. Green: the better. The dashed zero line is the tuned value.",
          "A short span near zero: a setting the model does not care about.",
          "Pick the model with the switch in the title. The tuned value is under each setting's name.",
        ],
        terms: ["tuning"],
      },
      {
        id: "calibration",
        title: "Are the probabilities honest?",
        shows: "Held-out women grouped into tenths by predicted chance: each point is a group's average prediction against the share who really reached the rung.",
        read: [
          "On the diagonal, a predicted 30% means 30%.",
          "Above it the model is too cautious; below it, too confident.",
          "Hover a model's name in the key to pick out its line.",
        ],
        terms: ["calibration"],
      },
      {
        id: "decision",
        title: "Is the model worth acting on?",
        shows: "A decision curve for this predictor set's best model on the held-out women, with logistic regression beside it. Along the bottom: how sure you want to be before acting on a woman. Up the side: the net benefit.",
        read: [
          "The model helps wherever its line sits above both **Act on everyone** (dashed) and **Act on no one** (flat).",
          "When the two lines lie together, the simpler model serves as well.",
          "Read it at the risk level your programme would act at.",
        ],
        terms: ["net-benefit", "decision-curve"],
      },
      {
        id: "lean",
        title: "What the models lean on",
        shows: "Each predictor's share of what each model uses, for the chosen predictor set and rung, on the held-out women.",
        read: [
          "Logistic regression and explainable boosting split their own predictions exactly, so their shares are the models' own arithmetic. Random forest and XGBoost are split by SHAP.",
          "Rows are the predictors the models agree on most, best first. A row dark in every column is a predictor all the models rely on.",
          "One shading for the whole grid, so any two cells compare.",
        ],
        terms: ["shap", "logistic", "ebm"],
      },
    ],
  },
  {
    key: "cohorts",
    label: "Cohorts & horizons",
    group: "explore",
    blurb: "Does the answer change with who is counted, and when?",
    screen: "/explore/cohorts",
    purpose:
      "Checks whether the study's answers depend on choices: which women are counted (full cohort, women who started care, births in the last 24 months) and when the prediction is made (before care starts, or at the first visit). It also shows that the 24-month cohort reproduces the official survey report.",
    before: ["basics-ladder", "basics-models"],
    cards: [
      {
        id: "tiles",
        title: "The three cohorts",
        shows: "Each cohort's size, what it is, and its share reaching each rung.",
        read: ["Click a tile to switch the whole studio to that cohort (the same as the sidebar's Cohort switch)."],
        terms: ["cohort", "window24"],
      },
      {
        id: "ladder",
        title: "The ladder in each cohort",
        shows: "One row per rung; one dot per cohort, with its 95% interval.",
        read: [
          "The ANC-entry cohort starts at ANC1+ by definition, so its ANC4+ and ANC8+ are higher: they are shares of women who started.",
          "Click a rung to switch to it.",
        ],
        terms: ["ci"],
      },
      {
        id: "contacts",
        title: "Contact counts in each cohort",
        shows: "The share of women with each number of contacts, one line per cohort.",
        read: ["The full and 24-month lines nearly coincide; the ANC-entry line has no zero and so sits higher everywhere else."],
      },
      {
        id: "regions",
        title: "Region by region, three cohorts",
        shows: "Each region's share reaching the rung in the three cohorts.",
        read: [
          "The number at the right: the 24-month cohort minus the full cohort, in points.",
          "Where the full-cohort dot sits left of the 24-month dot, older births did worse. In Tigray those pregnancies fell in the war.",
          "Click a region to select it.",
        ],
      },
      {
        id: "edhs",
        title: "The 24-month cohort reproduces the EDHS report",
        shows: "ANC4+ by region: the official report's table (rings) against this study's 24-month cohort computed from the raw data (dots).",
        read: [
          "Matching them is the check that the cohort, the weights and the contact count are built as the survey builds them.",
          "The tag gives the average gap in points.",
        ],
        terms: ["dhs", "window24", "weight"],
      },
      {
        id: "first-visit",
        title: "What the first visit adds",
        shows: "Predicting at the first visit adds one fact: whether it came in the first three months. Rings: held-out accuracy without it. Dots: with it.",
        read: ["Under each predictor set: the gain and its 95% interval. An interval above zero is a real gain."],
        terms: ["horizon"],
      },
      {
        id: "train-on",
        title: "Train on everyone, or only on women who started?",
        shows: "Two models scored on the same women who started care: one trained on the whole cohort (ring), one only on women who started (dot).",
        read: [
          "Accuracy is close; the difference is calibration.",
          "Under each row, calibration-in-the-large (0 is perfect): the whole-cohort model underestimates women who have already started.",
        ],
        terms: ["calibration"],
      },
      {
        id: "moments",
        title: "What each moment selects",
        shows: "Forward selection run separately for the two prediction moments: before care starts (left) and at the first visit (right).",
        read: [
          "Bars are the accuracy each predictor adds when it joins, in step order from the top.",
          "At the first visit, its timing (purple) enters near the front of the queue.",
        ],
        terms: ["forward-selection", "horizon"],
      },
    ],
  },
];
