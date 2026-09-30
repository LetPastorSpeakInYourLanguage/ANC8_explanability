import type { HelpTopic } from "./types";

/** The models: Model analysis, Predict, the First-visit screener, About. */

export const MODELS: HelpTopic[] = [
  {
    key: "analysis",
    label: "Model analysis",
    group: "models",
    blurb: "One model at a time: accuracy, honesty, how it was built",
    screen: "/models?rung=anc8",
    purpose:
      "A full report card for any one model at any rung: how much better than chance it ranks women, whether its percentages can be taken at their word, what happens at its working threshold, how it was built and tuned, and where it works well or less well. Compare it with a second model at any time.",
    before: ["basics-models", "basics-charts"],
    recipes: [
      {
        title: "Is this model good enough to use?",
        steps: [
          "Pick the model and rung. Read the four tiles: average precision and AUROC well above chance, and a calibration slope near 1.",
          "In **Against chance**, choose **Gains**: if you follow up the top 20% it ranks, what share of the women you are looking for do you reach?",
          "In **Differences, with intervals**, see whether it is really better than the best model and than logistic regression, or tied.",
          "In **Where it works**, check it does not fail a region or a wealth group.",
        ],
      },
      {
        title: "Compare two models",
        steps: ["Choose a second model in **Compare**. Its curve appears in purple in **Against chance**."],
      },
    ],
    cards: [
      {
        id: "picker",
        title: "Choosing the model",
        shows: "The controls along the top.",
        read: [
          "**Model**: every model in the library, grouped by kind. Within a group, the best at this rung comes first.",
          "**Predictors**: which predictor set the model was trained on. **Full pool** is every candidate predictor; **21 set** the 21-predictor set; **Short set** the strongest few that clear the bar at this rung; **Parsimonious** a small set chosen to keep accuracy with fewer questions. Switching the set keeps the same kind of model in view.",
          "**ANC1+ | ANC4+ | ANC8+**: the rung.",
          "**Compare**: a second model, on the same predictor set, to draw beside the first.",
          "Tags at the right: \"best at\" the rung if it is the top model, its kind, and its number of predictors.",
          "If a model is not in the library for the chosen set and rung, a note says so and the best model is shown instead.",
        ],
        terms: ["trees", "logistic", "network"],
      },
      {
        id: "tiles",
        title: "The model in four numbers",
        shows: "Its held-out average precision, AUROC, how many of the target women its top 20% holds, and its calibration slope.",
        read: [
          "**Average precision**: with chance, how many times chance it is (×), and its 95% interval.",
          "**AUROC**: chance is 0.500.",
          "**Top 20% hold**: follow up the fifth of women it ranks highest, and this is the share of the women you are looking for that you reach. Chance is 20%.",
          "**Calibration slope**: 1 is honest; the note says whether it is too confident or too cautious.",
        ],
        terms: ["ap", "auroc", "calibration-slope"],
      },
      {
        id: "curves",
        title: "Against chance",
        shows: "Three views of how much better than chance the model ranks women, chosen with the switch in the title.",
        read: [
          "**Gains**: rank women by the model and follow up the best-ranked first. The line is the share of the women you are looking for that you have found. The dashed diagonal is picking at random; the faint dashed line is a perfect ranking. The dotted mark is the top 20%.",
          "**ROC**: hits against false alarms. The diagonal is a coin toss.",
          "**Precision–recall**: of the women flagged, how many were right, at each level of recall. The flat dashed line is random flagging.",
          "With a comparison model chosen, its line is purple. Hover a name in the key to pick it out.",
        ],
        terms: ["roc", "precision-recall", "chance"],
      },
      {
        id: "calibration",
        title: "Honest probabilities?",
        shows: "Held-out women in ten equal groups by predicted chance: each dot is a group's average prediction against the share who really reached the rung.",
        read: [
          "On the diagonal, a predicted 30% means 30%.",
          "Above it the model is too cautious; below it, too confident.",
        ],
        terms: ["calibration", "calibration-slope"],
      },
      {
        id: "threshold",
        title: "At the working threshold",
        shows: "What happens when the model's chance is turned into a yes or no at its working threshold, on the held-out women.",
        read: [
          "The four boxes are shares of all women: right yes (green), false alarm, missed, right no (green).",
          "**Sensitivity**: of the women the model looks for, the share it called. **Specificity**: of the others, the share it correctly left alone.",
          "**PPV**: when it says yes, how often it is right. **NPV**: when it says no, how often it is right.",
          "The threshold was set on the development women and applied once.",
        ],
        terms: ["operating-threshold", "sensitivity", "ppv"],
      },
      {
        id: "tuning",
        title: "How it was built",
        shows: "What kind of model it is, how its inputs were prepared, and how its settings were searched.",
        read: [
          "The first two lines describe the model and how it handles numbers and categories.",
          "The tags: how many settings were tried, the five cluster-based folds, the score used, and how long the search took.",
          "Each bar is the range a setting was allowed to take, with the winning value marked; for settings with a few choices, the chosen one is blue.",
          "**What tuning bought**: library defaults (ring) against tuned (dot).",
          "Below, each setting moved one step either way: a span near zero is a setting the model does not care about.",
          "Networks show their training settings instead.",
        ],
        terms: ["tuning", "cv"],
      },
      {
        id: "where-works",
        title: "Where it works",
        shows: "The model's AUROC inside each group of held-out women, against its overall AUROC (dashed).",
        read: [
          "Group by region, wealth, education or residence.",
          "A dot well left of the dashed line: the model ranks women in that group less well.",
          "Faded rows rest on fewer than 60 women; groups under 25 are left out. Small groups are noisy.",
        ],
        terms: ["auroc"],
      },
      {
        id: "dev-held",
        title: "Development against held-out",
        shows: "This model at each rung: its accuracy on the development women (ring) and on the held-out women (dot).",
        read: [
          "A long line from ring to dot is optimism.",
          "Under each rung: its rank among all models there.",
          "Click a rung to switch to it.",
        ],
        terms: ["optimism", "heldout", "cv"],
      },
      {
        id: "vs-chance",
        title: "All models against chance",
        shows: "Every model at this rung, ranked by held-out average precision, with 95% intervals.",
        read: [
          "The dashed line is chance.",
          "Overlapping intervals: the models cannot really be told apart.",
          "Click a model to look at it.",
        ],
        terms: ["ap", "ci", "chance"],
      },
      {
        id: "differences",
        title: "Differences, with intervals",
        shows: "This model's average precision and AUROC minus the best model's and minus logistic regression's, on the same held-out women.",
        read: [
          "An interval that crosses zero means the two cannot be told apart.",
          "Empty for the model everything else is compared with.",
        ],
        terms: ["paired"],
      },
      {
        id: "grid",
        title: "Every model, every rung",
        shows: "Held-out average precision for every model on the chosen predictor set, at the three rungs.",
        read: [
          "Each column is shaded on its own, since rungs differ in difficulty.",
          "Click a row to look at that model; click a column title to switch rung.",
        ],
      },
      {
        id: "learned",
        title: "What it learned from",
        shows: "The women, the outcome and the predictors behind these numbers.",
        read: [
          "How many development and held-out women, the share reaching the rung (the chance level), and how many predictors.",
          "For the three models themselves, the predictors each leans on most, as shares of its total: exact for logistic regression, by SHAP for random forest and XGBoost.",
          "Links to the Explore screens with the wider story.",
        ],
        terms: ["shap"],
      },
    ],
  },
  {
    key: "predict",
    label: "Predict",
    group: "models",
    blurb: "Score one woman and see why",
    screen: "/predict",
    purpose:
      "Choose what to predict, when, and with which model, then change a woman's answers and watch her chance respond, with an exact breakdown of what each answer adds. It is for understanding the models, not for judging a real person.",
    before: ["basics-models"],
    recipes: [
      {
        title: "See what one answer is worth",
        steps: [
          "Keep the recommended model (★) and the starting woman.",
          "Change one answer, for example travel time to a health post.",
          "Read the change in points under her chance, and the new bar in **Why, exactly**.",
          "Press **Reset** to go back to the starting woman.",
        ],
      },
      {
        title: "Do the models agree?",
        steps: ["Press **Compare** in **Every … model** to score the same answers with every model for the question."],
      },
    ],
    cards: [
      {
        id: "questions",
        title: "The questions",
        shows: "The outcome, the moment, the model, and the answers it asks for.",
        read: [
          "**Outcome**: ANC1+, ANC4+ or ANC8+.",
          "**When**: before antenatal care starts, or at the first visit (adds whether the first visit was early). Not offered for ANC1+.",
          "**Model**: ★ marks the study's recommended model; \"instant\" models run in your browser; each shows its held-out average precision.",
          "The tags under it: its accuracy, number of predictors, where it runs, and **How it was built** (its Model analysis).",
          "The questions are grouped by theme, most influential first. A blue edge marks an answer you changed. **Show more** reveals the rest.",
          "The starting woman is a synthetic profile close to the survey's typical woman.",
        ],
        terms: ["predictor", "horizon"],
      },
      {
        id: "chance",
        title: "Chance of reaching the rung",
        shows: "The chosen model's chance for women with these answers.",
        read: [
          "The large number is her chance; under it, the change from the starting woman.",
          "The dashed line is the rate for all women; the ring is the model's working threshold.",
          "Any unanswered questions are filled with typical values, and it says how many.",
        ],
        watch: "It describes women with these recorded answers, not what would happen if a woman's circumstances changed.",
        terms: ["probability", "operating-threshold"],
      },
      {
        id: "why",
        title: "Why, exactly",
        shows: "What each answer adds to her score, largest first. Only for models that run in your browser.",
        read: [
          "Green bars raise her chance; red bars lower it.",
          "The numbers are on the log-odds scale: with the model's starting value they add up exactly to the number behind the percentage.",
        ],
        terms: ["log-odds", "logistic"],
      },
      {
        id: "compare",
        title: "Every model for the question",
        shows: "The same answers scored by every model for this outcome and moment.",
        read: [
          "Press **Compare** (then **Refresh** after changing answers).",
          "Models that roughly agree make the answer more believable.",
          "Click a model to switch to it.",
        ],
      },
    ],
    faq: [
      { q: "Some models are greyed out in the list.", a: "They need the prediction service, which this copy of the site does not have. Choose one marked instant." },
    ],
  },
  {
    key: "screener",
    label: "First-visit screener",
    group: "models",
    blurb: "Twelve questions that rank a register for follow-up",
    screen: "/your-data?mode=register",
    purpose:
      "Twelve questions a midwife can ask at a woman's first antenatal visit give almost the accuracy of the full survey model. Load a register of women and get a follow-up list ranked by each woman's chance of stopping early, with her main reasons. The file never leaves your computer.",
    before: ["basics-models"],
    recipes: [
      {
        title: "Make this week's call-back list",
        steps: [
          "Click **Template** and fill in one row per woman (or start from the synthetic sample to see how it works).",
          "Click **Load a register** and choose the file.",
          "Choose **Stop before 4** or **Stop before 8**.",
          "The **Follow-up list** puts the women most likely to stop first. Click one for her reasons and what might help.",
        ],
      },
    ],
    cards: [
      {
        id: "register",
        title: "Register",
        shows: "The file of women to screen: the synthetic sample, or yours.",
        read: [
          "One row per woman at her first visit. The columns are the twelve questions: region, age, previous births, minutes to a facility, household items (0–5), whether the first visit was early, education, whether the pregnancy was wanted then, transport, insurance, residence and marital status.",
          "**Template** downloads an example; **Load a register** reads your file here in the browser.",
          "**Stop before 4 | Stop before 8** chooses which drop-out to screen for.",
          "The sample is 300 made-up women drawn from the survey's own patterns; no row is a real person.",
        ],
        terms: ["screener"],
      },
      {
        id: "tiles",
        title: "The register in four numbers",
        shows: "How many women were screened, how many are expected to reach the rung, how many are at high risk, and how well the screen sorts women.",
        read: [
          "**High risk of stopping**: women with an 80% or higher chance of stopping early.",
          "**How well the screen sorts**: its AUROC on held-out women, with the full model's for comparison.",
        ],
        terms: ["auroc"],
      },
      {
        id: "list",
        title: "Follow-up list",
        shows: "The 25 women most likely to stop before the chosen rung, highest risk first.",
        read: [
          "**Main reasons**: the answers that raise her risk most.",
          "**Stops early**: her chance of stopping. Red is 80% or more, orange 50% or more, green below.",
          "Click a woman to see all her answers.",
        ],
        watch: "A score describes women like her, not her. Use it to decide who to call, not who to care for.",
      },
      {
        id: "why",
        title: "Why this chance",
        shows: "For the chosen woman: how each answer pushes her chance of reaching the rung, compared with a typical woman.",
        read: [
          "Bars to the right raise it; to the left lower it.",
          "**If one thing were different**: her chance if she were insured, lived within 30 minutes of care, if the pregnancy had been wanted then, or if next time her first visit is early. \"Same\" means no change.",
        ],
        watch: "These are associations in the survey, not promises.",
        terms: ["association"],
      },
      {
        id: "spread",
        title: "Spread of risk in this register",
        shows: "How many women fall in each band of risk of stopping early.",
        read: ["Green bands are low risk, orange middling, red high. A register heavy on the right needs more follow-up capacity."],
      },
      {
        id: "tested",
        title: "The screen, tested",
        shows: "The screen's accuracy on 984 held-out women who started care, against chance and against the model that uses every predictor.",
        read: [
          "Ring: chance. Dot: the twelve-question screen. Purple ring: all predictors.",
          "The screen sits close to the full model: it does not need a survey.",
        ],
        terms: ["ap", "heldout"],
      },
    ],
  },
  {
    key: "about",
    label: "About the study",
    group: "models",
    blurb: "The study on one page, and where each finding lives",
    screen: "/about",
    purpose:
      "A one-page summary of the study for a reader who wants the findings before the tools. It lists each finding with a link to the tool that shows it, the study's limits, the full written reports to download, and a short list of terms. Open it from the status bar or the finder.",
    cards: [
      {
        id: "findings",
        title: "Where to see each finding",
        shows: "One line per finding, and the tool that shows it. Click a line to open it.",
        read: ["The numbers come from the studio's own data files, so they match the tools."],
      },
      {
        id: "limits",
        title: "Limits",
        shows: "What the study cannot support, each linked to the tool where it matters.",
        read: [
          "Scenarios are associations, not causes.",
          "One survey round: whether the accuracy holds on another round is untested.",
          "Contact counts are recalled by the women, and older births less well.",
          "Conflict elsewhere is assumed to act as it did in Tigray.",
        ],
      },
      {
        id: "reports",
        title: "Full reports",
        shows: "The written study as plain text files, for reviewers: brief, findings, methods, data, predictors and more.",
        read: ["Click a name to download it."],
      },
    ],
  },
];
