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
    plain: [
      "The three rungs are cuts through one number: how many antenatal visits each woman had. The ladder screen shows that number whole, so you can see where women stop, not just whether they passed a line.",
      "Women bunch at three or four visits, and again at eight: the first bunch sits at the old four-visit standard, the second at the new eight-visit one.",
      "Following a group of women up the ladder (the poorest fifth, say) shows where that group is lost. A group that starts care as often as others but falls away before eight needs help staying, not starting.",
    ],
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
        plain: [
          "Line up the held-out women from most to least likely to reach the rung, as the model sees them. **Average precision** asks how many of the women near the top of that list really did reach it, averaged all the way down. Guessing gives the share who reach the rung: 16% of the held-out women reached eight visits. The best model scores 0.44, close to three times chance.",
          "ANC8+ is the hardest rung to predict in absolute terms, but it is where the model adds most over guessing.",
        ],
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
        plain: [
          "Each model's own account of what it uses, summed into groups (access, wealth, education and so on) and shown as shares of the whole. A group whose line rises from ANC1+ to ANC8+ matters more for going further up the ladder than for starting.",
          "Logistic regression's shares are its own arithmetic. For random forest and XGBoost the shares come from SHAP, a standard way of splitting a tree model's prediction into a part per predictor. When all three models agree, the finding does not depend on the kind of model.",
        ],
        title: "What matters at each rung",
        shows: "One line per group of predictors (access and distance, wealth, education, reproductive history and so on): its share of what the model uses at each rung.",
        read: [
          "A line that rises from ANC1+ to ANC8+ matters more for going further up the ladder.",
          "Hover a name in the key to pick its line out.",
          "**Measured by**: each model's own account on the 21 predictors (logistic regression splits its predictions exactly; random forest and XGBoost by SHAP), or the accuracy lost when the group is removed (Drop-one). Where they agree, the finding is solid.",
        ],
        terms: ["logistic", "shap", "drop-one"],
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
    key: "models",
    label: "Models compared",
    group: "explore",
    blurb: "Every model at every rung",
    screen: "/explore/models?rung=anc8",
    purpose:
      "Every model the study built, side by side and honestly: on the development women that tuning saw, and on the held-out women nothing saw. It also shows what tuning bought, whether the probabilities can be trusted, and whether a model is worth acting on. For one model in depth, use Model analysis.",
    plain: [
      "Before any model was built, a fifth of the survey's clusters (1,375 women) were set aside and never looked at. Every model was then built and tuned on the other 5,518 women, and scored once on the held-out women. A model that looks much better on the women it was built on than on the held-out women has learned noise.",
      "Three kinds of model are compared: logistic regression (each answer adds a fixed amount to a woman's score), random forest (many decision trees voting) and XGBoost (small trees added one at a time, each fixing the last one's mistakes). They finish close together: at ANC8+ their held-out scores lie between 0.41 and 0.44, and their 95% ranges overlap.",
    ],
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
        ],
        terms: ["ap", "lift", "auroc", "brier"],
      },
      {
        id: "tuning",
        plain: [
          "Each model has settings, such as how many trees or how strongly to hold back from fitting noise. The study fixed a small list of settings to try in advance, tried every combination on the development women, and kept the best. **Does tuning pay?** compares each model with its default settings against the chosen ones: most gains are small, which means the models are not fragile.",
        ],
        title: "Does tuning pay?",
        shows: "Each model with its default settings (ring) and after tuning (dot), on the development women and the 21 predictors.",
        read: ["Most gains are small: the models are close before and after tuning."],
        terms: ["tuning"],
      },
      {
        id: "settings",
        title: "Which settings matter",
        shows: "For the chosen model, each tuned setting moved one step down and one step up while the others stay fixed (development women, the 21 predictors).",
        read: [
          "Red dot: the worse of the two neighbours. Green: the better. The dashed zero line is the tuned value.",
          "A short span near zero: a setting the model does not care about.",
          "Pick the model with the switch in the title. The tuned value is under each setting's name.",
        ],
        terms: ["tuning"],
      },
      {
        id: "calibration",
        plain: [
          "Sort the held-out women into ten groups by their predicted chance. If the model is honest, the group it gives 30% should have about 30% of women reaching the rung. Points below the diagonal: the model promised more than happened (too confident). Points above: less (too cautious).",
        ],
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
        plain: [
          "A decision curve asks whether acting on the model beats the two simple policies: follow up everyone, or no one. Along the bottom is how sure you want to be before acting on a woman. The height is the net benefit: women correctly acted on, minus a penalty for false alarms that depends on how sure you wanted to be.",
          "Where the model's line sits above both simple policies, using the model helps. Where it sinks to them, you may as well treat everyone the same.",
        ],
        title: "Is the model worth acting on?",
        shows: "A decision curve for the best model on the held-out women, with logistic regression beside it. Along the bottom: how sure you want to be before acting on a woman. Up the side: the net benefit.",
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
        shows: "Each predictor's share of what each model uses, for the chosen rung, on the held-out women.",
        read: [
          "Logistic regression splits its own predictions exactly, so its shares are the model's own arithmetic. Random forest and XGBoost are split by SHAP.",
          "Rows are the predictors the models agree on most, best first. A row dark in every column is a predictor all the models rely on.",
          "One shading for the whole grid, so any two cells compare.",
        ],
        terms: ["shap", "logistic"],
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
    plain: [
      "Which women are counted changes the numbers a little, so the studio keeps three cohorts. **Full**: every woman whose most recent birth, up to five years before the survey, has a recorded number of visits (6,893 women). **24 months**: births in the last two years, the window the national survey report uses. **ANC entry**: the 5,001 women who started care and whose first-visit timing is known, for predicting at the first visit.",
      "Older births are remembered less well and, in Tigray, fell in the war, so the 24-month cohort is the one to compare with official figures. The studio's 24-month numbers reproduce the official report's table region by region, which checks that the cohort, the weights and the visit counts are built the way the survey builds them.",
    ],
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
        read: ["Under the 21: the gain and its 95% interval. An interval above zero is a real gain."],
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
