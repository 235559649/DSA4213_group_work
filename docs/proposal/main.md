::: center
**Group Project Proposal**\
Improving Repository Navigation and Bug Localization in Minimal Software
Engineering Agents\
Group ID: 25\
DSA4213: Natural Language Processing for Data Science\
Semester 1, AY2026/2027
:::

# Administrative Information {#administrative-information .unnumbered}

+:----------------+:--------------------------------------------------+
| Group members   | ZHANG YUHANG(A0351628B)                           |
+-----------------+---------------------------------------------------+
|                 | WANG CHI(A0357310M)                               |
+-----------------+---------------------------------------------------+
|                 | CHEN WENWEN(A0351705J)                            |
+-----------------+---------------------------------------------------+
|                 | JIANG ZHANGZHANG(A0355183B)                       |
+-----------------+---------------------------------------------------+
|                 | CHEN XINGYU(A0355370E)                            |
+-----------------+---------------------------------------------------+
| Project         | Software Engineering Agents -- Repository         |
| direction       | Navigation and Bug Localization.                  |
+-----------------+---------------------------------------------------+
| Repository      | <https://github.com/235559649/DSA4213_group_work> |
+-----------------+---------------------------------------------------+

# Project Summary {#project-summary .unnumbered}

Software engineering agents such as mini-SWE-agent can autonomously
explore repositories, modify code, and execute tests, but repository
exploration is largely driven by free-form shell interaction. This
project studies whether structured repository navigation and
failure-aware bug localization can improve the efficiency and
reliability of software repair agents. We will extend mini-SWE-agent
with a Python-oriented repository indexer that ranks relevant files and
functions based on issue descriptions, code structure, and runtime
failure evidence. We will compare the proposed agent with the original
mini-SWE-agent on real bug-fixing tasks, evaluating repair success rate,
localization accuracy, number of explored files, shell commands, token
usage, runtime, and failure patterns.

# 1. Problem, Research Question, and Motivation {#problem-research-question-and-motivation .unnumbered}

[**TODO:** CHEN WENWEN]{style="color: red"}

Software engineering agents must often explore a large repository before
they can determine which files or functions are responsible for a
reported bug. A minimal agent such as mini-SWE-agent can perform this
exploration using shell commands and language-model reasoning, but the
navigation process is not explicitly optimized for locating relevant
code.

Our project focuses on the repository exploration and bug localization
stage of the software repair process. Rather than replacing the existing
repair capability of mini-SWE-agent, we investigate whether additional
repository structure and runtime failure evidence can help the agent
reach relevant code more efficiently.

[**TODO:** Add a short motivating example showing an issue where the
agent must search through several files before reaching the correct
function.]{style="color: red"}

## 1.1 Primary Research Question {#primary-research-question .unnumbered}

**RQ1.** Can structured repository navigation and runtime failure
evidence help mini-SWE-agent localize relevant code more efficiently
without reducing bug-fixing success?

## 1.2 Secondary Research Questions {#secondary-research-questions .unnumbered}

**RQ2.** Does improved localization reduce repository exploration cost,
measured by the number of files inspected, shell commands executed,
token usage, and runtime?

**RQ3.** Which information sources contribute most to successful
localization: textual relevance to the issue, static repository
structure, or runtime failure evidence?

## 1.3 Definition of Success {#definition-of-success .unnumbered}

The project will be considered successful if the proposed system can
either improve bug localization and repair performance, or achieve
comparable repair performance while reducing unnecessary repository
exploration.

[**TODO:** Define quantitative success criteria after pilot experiments,
for example an improvement in Top-$k$ localization accuracy or a
reduction in exploration steps.]{style="color: red"}

# 2. Related Work and Proposed Contribution {#related-work-and-proposed-contribution .unnumbered}

[**TODO:** WNAG CHI]{style="color: red"}

## 2.1 mini-SWE-agent {#mini-swe-agent .unnumbered}

mini-SWE-agent will serve as the primary baseline and software repair
agent in this project.

[**TODO:** Describe the mini-SWE-agent architecture, its minimal agent
loop, available tools, and how repository exploration is performed. Add
the appropriate citation.]{style="color: red"}

[**TODO:** Clarify exactly which parts of mini-SWE-agent are reused
without modification and which integration points will be changed by our
system.]{style="color: red"}

## 2.2 SWE-bench {#swe-bench .unnumbered}

SWE-bench provides real-world software engineering tasks based on
repository issues and corresponding code changes.

[**TODO:** Describe the chosen SWE-bench version/subset and justify why
it is appropriate for evaluating our project. Add
citation.]{style="color: red"}

[**TODO:** Specify whether the project will use SWE-bench Verified or
another subset, and how many tasks will be used for development and
evaluation.]{style="color: red"}

## 2.3 Repository Localization Methods {#repository-localization-methods .unnumbered}

Previous software engineering agents and code-retrieval systems have
used techniques such as lexical search, semantic retrieval, repository
structure, dependency information, and execution feedback to identify
code relevant to a software issue.

[**TODO:** Review and cite the most relevant repository navigation / bug
localization systems. Include systems that are particularly close to our
proposed approach so that our novelty is clearly
stated.]{style="color: red"}

[**TODO:** Explain how our approach differs from prior work rather than
only listing related systems.]{style="color: red"}

## 2.4 Our Contribution {#our-contribution .unnumbered}

- A Python-oriented repository indexer that extracts structural
  information at the file, class, and function levels and supports
  task-aware localization of relevant code.

- A failure-aware localization mechanism that uses runtime evidence,
  including tracebacks and failing tests, to refine previously ranked
  suspicious code locations.

- An empirical study comparing repair performance and repository
  exploration efficiency against the original mini-SWE-agent baseline.

[**TODO:** Finalize the exact ranking algorithm before submission. For
example, decide whether C1 combines keyword similarity, semantic
similarity, repository structure, or another scoring
method.]{style="color: red"}

# 3. Agent and Task Setup {#agent-and-task-setup .unnumbered}

[**TODO:** ZHANG YUHANG]{style="color: red"}

## 3.1 Task {#task .unnumbered}

The agent receives a software issue together with a Python repository.
Its goal is to identify the code relevant to the issue, produce a patch,
and validate the patch through execution or tests.

**Input:** a natural-language issue description and the corresponding
repository.

**Output:** a proposed source-code patch and an execution trajectory
containing repository exploration, edits, and test results.

## 3.2 Operating Environment {#operating-environment .unnumbered}

The repair agent will operate inside an isolated execution environment
with access to the repository, shell commands, Python execution, Git,
and the repository's available test framework.

[**TODO:** Specify the exact environment, e.g., Docker / SWE-bench
containers, Python versions, and available system
tools.]{style="color: red"}

## 3.3 Agent and Model {#agent-and-model .unnumbered}

The original mini-SWE-agent will be used as the software repair
baseline. Our system will augment its repository exploration process
with structured localization information.

[**TODO:** Specify the LLM(s) used in experiments.]{style="color: red"}

[**TODO:** Specify whether all compared systems will use the same model,
temperature, token budget, and prompts to ensure a controlled
comparison.]{style="color: red"}

## 3.4 Agent Tools {#agent-tools .unnumbered}

The proposed system may provide the agent with the following sources of
information:

- shell-based repository exploration;

- file, class, and function indexing;

- Python AST and import information;

- issue-to-code relevance scores;

- test execution results; and

- traceback and runtime failure evidence.

[**TODO:** Remove any tool that is not implemented in the final system
and describe the exact interface exposed to the
agent.]{style="color: red"}

## 3.5 Benchmark and Task Selection {#benchmark-and-task-selection .unnumbered}

The initial study will focus on Python repositories so that Python ASTs,
tracebacks, and testing tools can be exploited consistently.

[**TODO:** Define the exact benchmark subset and task selection
criteria.]{style="color: red"}

[**TODO:** Specify the number of tasks used for pilot development and
final evaluation.]{style="color: red"}

## 3.6 Stopping Conditions and Failure Recovery {#stopping-conditions-and-failure-recovery .unnumbered}

An agent run may terminate when the target tests pass, when the agent
explicitly submits a final patch, or when a predefined resource budget
is exhausted.

When execution fails, the system can extract information from the
failure and use it to update the localization ranking before the next
repair attempt.

[**TODO:** Define maximum agent steps, token budget, runtime limit, and
the exact condition used to determine successful
repair.]{style="color: red"}

# 4. Proposed System or Study Design {#proposed-system-or-study-design .unnumbered}

[**TODO:** CHEN XINGYU]{style="color: red"}

The proposed workflow consists of an initial repository analysis stage,
a localization stage, the existing mini-SWE-agent repair process, and an
optional refinement stage based on runtime failures.

<figure data-latex-placement="htbp">

<figcaption>Proposed system architecture.</figcaption>
</figure>

## 4.1 Baseline {#baseline .unnumbered}

The baseline is the original mini-SWE-agent operating with its standard
repository exploration and repair loop.

[**TODO:** Describe the exact baseline configuration and ensure it uses
the same LLM and execution budget as the proposed
system.]{style="color: red"}

## 4.2 Repository Indexing {#repository-indexing .unnumbered}

Before repair begins, the repository indexer analyzes the Python
repository and records structural information such as:

- file paths;

- classes;

- functions and methods;

- import relationships; and

- selected code metadata relevant to localization.

[**TODO:** Define the actual internal representation. Decide whether
this will be a table, graph, JSON index, or another
structure.]{style="color: red"}

[**TODO:** Decide whether call relationships or inheritance information
are included. Avoid adding them unless they are actually
used.]{style="color: red"}

## 4.3 Initial Localization {#initial-localization .unnumbered}

Given an issue description, the localization module ranks repository
files and functions according to their estimated relevance to the issue.

The result will be a ranked list of suspicious locations that can be
provided to the repair agent as additional context.

[**TODO:** Define the localization scoring
function.]{style="color: red"}

[**TODO:** Decide whether the initial implementation includes keyword
search, semantic embeddings, structural signals, or a hybrid
method.]{style="color: red"}

## 4.4 Failure-Aware Refinement {#failure-aware-refinement .unnumbered}

If a reproduction attempt or test execution fails, the system extracts
runtime evidence such as:

- exception type;

- traceback frames;

- files and functions appearing in the traceback;

- failing test names; and

- relevant error messages.

This information is then used to update the ranking of suspicious code
locations.

[**TODO:** Define how runtime evidence modifies the original
ranking.]{style="color: red"}

[**TODO:** Provide one concrete example trajectory in the final proposal
if space permits.]{style="color: red"}

## 4.5 Repair Loop {#repair-loop .unnumbered}

The localized context is passed to mini-SWE-agent, which investigates
the repository, modifies source code, and executes tests. If the patch
fails, failure information may be returned to the localization component
and a new repair attempt can be made.

[**TODO:** Specify whether localization is performed only once or
repeatedly during the trajectory. This decision is important for the
final system design.]{style="color: red"}

## 4.6 Optional Extension: Reviewer Agent {#optional-extension-reviewer-agent .unnumbered}

If time permits, an independent reviewer agent may inspect a proposed
patch before final submission.

The reviewer would focus on correctness, whether the reported failure
has actually been addressed, potential regressions, and relevant edge
cases.

[**TODO:** Keep this as an optional extension. Do not make it part of
the main claim unless the core localization system is completed
early.]{style="color: red"}

## 4.7 Comparisons and Ablations {#comparisons-and-ablations .unnumbered}

The planned controlled conditions are:

- **Baseline A:** original mini-SWE-agent;

- **Baseline B:** mini-SWE-agent with simple lexical / keyword
  localization;

- **Method C:** mini-SWE-agent with repository-structure-aware
  localization;

- **Method D:** mini-SWE-agent with repository-structure-aware
  localization and failure-aware refinement.

Possible ablations will remove individual information sources from the
full system.

[**TODO:** Finalize comparison conditions after implementing a pilot
version. Do not promise more baselines than the group can realistically
run.]{style="color: red"}

[**TODO:** Possible ablations: no structural information, no failure
evidence, or file-level rather than function-level
localization.]{style="color: red"}

# 5. Preliminary Evaluation Plan {#preliminary-evaluation-plan .unnumbered}

[**TODO:** JIANG ZHANGZHANG]{style="color: red"}

The evaluation is designed to distinguish whether the proposed method
improves actual bug fixing, localization quality, or only repository
exploration efficiency.

## 5.1 Repair Performance {#repair-performance .unnumbered}

Potential measures include:

- issue resolution rate;

- target tests passed;

- regression-test performance; and

- number of successful repairs within the resource budget.

[**TODO:** Define the official repair-success criterion using the
selected benchmark's evaluation harness.]{style="color: red"}

## 5.2 Localization Performance {#localization-performance .unnumbered}

Potential localization metrics include:

- Top-1 relevant-file accuracy;

- Top-$k$ relevant-file accuracy;

- function-level localization accuracy; and

- rank of the ground-truth modified location.

[**TODO:** Define ground-truth localization from benchmark patches and
decide the value(s) of $k$.]{style="color: red"}

## 5.3 Exploration Efficiency {#exploration-efficiency .unnumbered}

We will measure the amount of repository exploration required before the
agent reaches relevant code.

Potential measures include:

- number of files opened;

- number of shell commands executed;

- number of agent / LLM steps;

- token usage;

- runtime; and

- estimated API cost.

[**TODO:** Select the final subset of efficiency measures to avoid
reporting too many redundant metrics.]{style="color: red"}

## 5.4 Agent-Trajectory Analysis {#agent-trajectory-analysis .unnumbered}

Aggregate metrics will be complemented with representative successful
and failed trajectories. We will examine, for example, whether failed
runs repeatedly inspect irrelevant files, fail to use runtime evidence,
or reach the correct code but produce an incorrect patch.

[**TODO:** Define a small failure taxonomy after observing pilot
trajectories.]{style="color: red"}

## 5.5 Variability and Experimental Protocol {#variability-and-experimental-protocol .unnumbered}

Because LLM-based agents may produce different trajectories across runs,
the comparison should control model configuration and resource budgets.

[**TODO:** Decide the number of repeated runs per task, subject to API
and compute cost.]{style="color: red"}

[**TODO:** Specify model version, temperature, maximum steps, token
budget, and random seeds where applicable.]{style="color: red"}

# 6. Risks, Limitations, and Responsible Practice {#risks-limitations-and-responsible-practice .unnumbered}

[**TODO:** CHEN WENWEN]{style="color: red"}

- **LLM nondeterminism.** Repeated runs may produce different
  trajectories and repair results. We will use controlled model settings
  and repeated evaluation where resources permit.

- **Benchmark contamination.** Public repositories or issue solutions
  may have appeared in model training data, so benchmark performance
  should not be interpreted purely as unseen-code generalization.

- **Execution safety.** Software engineering agents can execute shell
  commands. Experiments will therefore be conducted in isolated
  environments with restricted permissions.

- **API and compute cost.** Full agent trajectories can require
  substantial token usage and execution time. A fixed experimental
  budget will be used.

- **Environment failures.** Some benchmark repositories may fail because
  of dependency or setup problems unrelated to the agent itself. These
  cases will be logged separately where possible.

- **Python-specific scope.** The initial system focuses on Python
  repositories, so conclusions may not directly generalize to other
  programming languages.

## 6.1 Safeguards {#safeguards .unnumbered}

Experiments will use isolated execution environments, restricted
credentials and permissions, fixed resource budgets, and public
benchmark repositories only. No private repositories, credentials, or
confidential source code will be included[@sample2024].

[**TODO:** Confirm the exact sandbox/container mechanism used by the
final implementation.]{style="color: red"}

[**TODO:** Create references.bib and add citations for mini-SWE-agent,
SWE-bench, repository localization methods, and any additional systems
used by the project.]{style="color: red"}
