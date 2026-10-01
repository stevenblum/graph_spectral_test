# Applied Graph Spectral Analysis Curriculum

## Goal

Build a sequence of explanatory, executable Jupyter notebooks that teaches graph spectral analysis and the graph Fourier transform (GFT) through real-world problems. Establish what these methods reveal, when they are useful, and how modeling choices affect their interpretation.

Success means the learner can formulate a graph problem, choose and explain its spectral operator, implement the analysis, interpret the outputs in the application domain, and evaluate whether the method adds useful information. Computing eigenvalues or producing attractive plots alone is insufficient.

This file guides curriculum authors and coding agents. Implement the requested notebook or increment; the Case Study sequence below describes the overall progression.

## Notebook types

The repository holds three kinds of notebook. Material flows between them: Case Studies are condensed into Lessons, and an Experiment may be folded into a Lesson or grown into a Case Study.

- **Case Study** — `case_studies/`, numbered (`00_`, `01_`, …). A long, exploratory, self-paced notebook built around one application question and dataset. Everything in this file applies.
- **Lesson** — `lessons/`, numbered (`01_`, `02_`, …). One 20–30 minute slide presentation in a short introductory series (not a full course), presented as a reveal.js deck built with `lessons/make_slides.py`. The conventions and teaching approach apply in condensed form; slide layout follows `docs/agent_references/notebook_reveal_standard.md`. Superseded versions move to `lessons/archive/`, kept for reference and not maintained to run.
- **Experiment** — `experiments/`, not numbered. A specific application investigation, messier and less structured than a Case Study or Lesson. The mathematical conventions apply; the teaching approach and completion requirements are optional.

Helper modules and cached data live beside the Case Studies that created them (`case_studies/glearn.py`, `imcodec.py`, `data/`, `out/`); `lessons/temps.py` reuses them.

## Audience

- Researchers, engineers, and graduate students comfortable with Python and basic linear algebra, but new to spectral graph theory and graph signal processing.
- Assume familiarity with matrices and vectors; refresh eigenvectors, orthogonality, projections, and quadratic forms where needed.
- Explain graph terminology and Fourier concepts from fundamentals. Define every symbol, matrix dimension, unit, and modeling assumption.
- Transportation and human-driving research motivate the later applications, including eye-tracking scanpaths and semantic scene graphs. The core material should remain useful to other applied researchers.

## Teaching approach

- Begin each Case Study or Lesson with a concrete application question and an explicit mapping of data to nodes, edges, weights, coordinates, and signals.
- Follow the sequence: application question → mathematical model → executable calculation → visualization → interpretation → evidence of usefulness and limitations.
- Alternate concise Markdown explanations, essential LaTeX mathematics, short readable code cells, and interpreted results. Keep core calculations visible before introducing helper functions.
- Use small real datasets first. Clearly distinguish observed measurements, derived variables, benchmark solutions, and illustrative synthetic examples.
- Introduce one formulation at a time. Reuse datasets and operators when that isolates a new concept.
- Use reconstruction error, agreement with known communities, or another relevant comparison to assess usefulness. Do not assume every real signal is smooth or that spectral methods always outperform simple alternatives.
- Compare against a simpler non-spectral alternative wherever the comparison teaches something — when a notebook's headline claim is that the method worked, or when a reader could reasonably ask whether the graph was needed at all. Skip it where a section builds machinery, defines an operator, or makes an interpretive point rather than a performance claim; a baseline there is ritual. Choose the alternative a practitioner would reach for first, and report what you measure. A tie or a loss is the more instructive outcome and usually relocates the method's value away from accuracy.
- Report spectral quantities against a yardstick: a null model, an analytic bound, or a reference graph. An eigenvalue or an energy with no scale attached is not a finding. Randomizing the graph (degree-preserving rewiring) and randomizing the signal (permutation across nodes) answer different questions; say which one a null addresses.
- Explain both what an analysis supports and what it cannot establish; spectral patterns alone do not demonstrate causation, physical dynamics, or cognitive mechanisms.
- Keep functions and parameters easy to inspect and modify. Extensive graph-perturbation exercises are not required; the learner will explore these independently.
- Use short interpretation questions with suggested answers. Link relevant references beside the concepts they support.

## Case Study sequence

### 1. Static, unweighted graph topology

- **Question:** What can connectivity alone reveal about communities and structural bottlenecks?
- **Data:** [Zachary's Karate Club](https://networkx.org/documentation/stable/reference/generated/networkx.generators.social.karate_club_graph.html); optional [Email-Eu-core](https://snap.stanford.edu/data/email-Eu-core.html).
- **Model:** Static, simple, undirected, unweighted graph with no observed graph signal. For Karate, explicitly use `weight=None`; for Email-Eu-core, explain symmetrization and remove self-loops.
- **Concepts:** Adjacency and degree matrices; combinatorial and normalized Laplacians; eigendecomposition; zero eigenvalues and connected components; algebraic connectivity; Fiedler vector; spectral embedding and partitioning. Briefly distinguish adjacency and Laplacian spectra.
- **Dirichlet energy is introduced here**, in its edge form \(q^\top Lq=\sum_{\{i,j\}\in E}(q_i-q_j)^2\), as the quantity the eigenvectors minimize and the reason \(\lambda_k=u_k^\top Lu_k\) deserves the name graph frequency. No signal is required for this form. Reconcile the edge-sum and ordered-pair (\(\tfrac12\)) conventions, state its squared units and its \(\|q\|^2\) scaling, and note \(L=\nabla^\top\nabla\). Case Study 2 supplies the spectral form.
- **Calibration:** do not assert that \(\lambda_2\) is small. Compare it against the bound \(\lambda_2\le\tfrac{n}{n-1}d_{\min}\), reference graphs, and a degree-preserving rewiring null; do the same for the cut size. On Karate the bound is the binding constraint, and the honest conclusion differs from the one a bare eigenvalue suggests.
- **Outputs:** Matrix heatmaps, eigenvalue plots, eigenvectors shown as node colors, and a spectral partition compared with the observed club split. Labels are for evaluation only.
- **Reference:** von Luxburg [R1]. Suggested notebook: `01_graph_topology_spectrum.ipynb`.

### 2. Scalar signals on a fixed graph

- **Question:** Which graph-defined patterns explain an observed node quantity, and how compactly can it be represented?
- **Data:** Reuse Karate with binary club membership as the signal; extend to [MATPOWER IEEE 14-bus data](https://matpower.org/docs/ref/matpower5.0/case14.html), using demand, voltage magnitude, or voltage angle separately. Identify MATPOWER values as a benchmark operating case.
- **Concepts:** GFT and inverse GFT; orthogonal projection; Parseval's identity; graph-frequency bands; truncated reconstruction; low-pass and heat-kernel filtering.
- **Dirichlet energy returns in spectral form** \(x^\top Lx=\sum_k\lambda_k|\widehat{x}_k|^2\), which needs a signal and the GFT. Connect it explicitly to Case Study 1's edge form: same number, now resolved across frequencies. Compare signals by Rayleigh quotient, never by raw energy, and test smoothness against a signal-permutation null rather than assuming it.
- **Outputs:** Original signal, spectral coefficients and energies, reconstructed signals, and reconstruction error versus retained modes. Explain when smoothing removes meaningful discontinuities.
- **References:** Shuman et al. [R2]; Ortega et al. [R3].

### 3. Spatially embedded graph signals

- **Question:** How can an irregular sensor or geographic network represent spatial patterns and support estimation at unobserved locations?
- **Data:** [NOAA GHCN-Daily](https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily) weather stations, initially one date in New England; alternative [Census TIGER/Line polygons](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) joined to a scalar [ACS statistic](https://www.census.gov/data/developers/data-sets/acs-5year.html).
- **Concepts:** Coordinates versus graph topology; geographic distance versus graph distance; k-nearest-neighbor, radius, Delaunay, and contiguity constructions. Start with unweighted edges. Use projected or geodesic distances appropriately.
- **Outputs:** Maps of measurements and eigenmodes, spectral energy, and spatial reconstruction. Where practical, evaluate held-out measurements against a simple spatial baseline. Keep graph construction independent of held-out values.
- **Key point:** Coordinates affect the spectral basis only through the operator; merely moving nodes in a drawing does not change its spectrum. Coordinates may also be analyzed as signals. Geographic graphs model relationships rather than automatically supplying a physical law.
- **References:** [R2–R3] and the dataset documentation.

### 4. Weighted transportation graphs

- **Question:** How does the definition of connection strength change inferred network structure and accessibility?
- **Data:** [Sioux Falls TNTP](https://github.com/bstabler/TransportationNetworks/tree/master/SiouxFalls) as a small benchmark; a real OpenStreetMap street network retrieved with [OSMnx](https://osmnx.readthedocs.io/en/stable/) as an extension.
- **Concepts:** Weighted degree and Laplacians; costs versus affinities; capacity, travel time, and flow as distinct quantities; normalized versus combinatorial operators; spectral cuts and diffusion. Introduce direction only after symmetric operators are understood.
- **Outputs:** Compare justified weight definitions using spectra, partitions, and network maps. Explain what each definition measures. Sioux Falls is a debugging benchmark, not realistic measured traffic; OSM-derived travel times may use imputed speeds.
- **Bridge:** An observed road-link value is an edge signal unless deliberately used to define the operator. Introduce line graphs and oriented incidence matrices briefly; reserve full edge-flow analysis for Case Study 5B.
- **References:** [R3–R4] and the [TNTP format documentation](https://github.com/bstabler/TransportationNetworks).

### 5A. Fixed graph with time-varying node signals

- **Question:** What traffic patterns vary across the network, through time, or along both dimensions?
- **Data:** [METR-LA or PEMS-BAY](https://github.com/liyaguang/DCRNN): sensors as nodes and speed observations through time. Inspect supplied graph direction and document any symmetric adaptation for the initial Laplacian GFT.
- **Concepts:** A fixed basis applied to each column of a node-by-time matrix; graph-frequency versus temporal-frequency axes; joint time–vertex transform; filtering and reconstruction.
- **Outputs:** Sensor-by-time heatmap, graph-frequency-by-time energy, joint spectrum, and selected-band reconstructions. Compare spatial-only, temporal-only, and joint methods on an appropriate reconstruction task.
- **References:** Grassi et al. [R5]. DCRNN [R6] supplies traffic context and a directed-diffusion comparison; training that neural network is not required.

### 5B. Fixed graph with time-varying edge signals

- **Question:** How do road-link conditions and directed flows vary across a transportation network?
- **Data:** [pNEUMA vehicle trajectories](https://open-traffic.epfl.ch/), mapped to a fixed road graph and aggregated into link measurements over time. Budget explicitly for map matching and aggregation; this is not a ready-made edge-signal matrix.
- **Concepts:** Edge-by-time matrices; line-graph representations for link attributes; incidence and Hodge operators for oriented flows; divergence and conservation; temporal analysis of edge modes.
- **Outputs:** Link maps, spectral reconstructions, and flow-balance diagnostics. Account for sources, sinks, and accumulation; low divergence is not universally the correct traffic assumption.
- **Key point:** Scalar speed and signed flow require different interpretations. A full gradient/curl/harmonic decomposition needs a declared cell or simplicial structure, not just arbitrary road triangles.
- **Reference:** Schaub and Segarra [R4]. Their London example uses synthetic flows on a street network.

### 5C. Changing graph topology or operator — advanced extension

- **Question:** How can spectral analysis describe changing vehicle interactions when the basis itself evolves?
- **Data:** [I-24 MOTION](https://i24motion.org/) trajectories; nodes represent vehicles and edges encode explicitly defined proximity or driving relationships.
- **Concepts:** Changes in node identity, edges, and weights; snapshot operators; eigenvector signs, repeated eigenspaces, and mode crossings; fixed reference representations and temporal alignment.
- **Outputs:** Explain what changes at each time and demonstrate an explicit comparison strategy. A fixed union graph stabilizes indexing; it supplies a common basis only if its operator is also fixed.
- **References:** Dataset paper [R7]; use [R5] to contrast fixed-graph time–vertex analysis with this harder formulation.

### Optional capstone: driving gaze analysis

- Apply the learned methods to event-aligned gaze scanpaths using a common path graph with gaze coordinates as signals, then to a fixed AOI/semantic graph with attention through time.
- Specify whether nodes index time samples or fixations; represent fixation duration consistently with that choice. Preserve a common basis for comparisons across drivers, roundabout locations, and distraction conditions.
- Connect spectral features to interpretable gaze behavior and evaluate with participant-grouped validation. Typed graphs and cellular sheaves are later extensions, not prerequisites for the core curriculum.

## Essential mathematical conventions

For a loop-free undirected graph with symmetric nonnegative weights, use:

\[
D_{ii}=\sum_j W_{ij},\qquad L=D-W=U\Lambda U^\top.
\]

- An unweighted graph has binary `W = A`. For the combinatorial Laplacian, order eigenvalues as \(0=\lambda_1\leq\lambda_2\leq\cdots\).
- Graph spectrum means the operator's eigenvalues; a node signal is required to compute \(\widehat{x}=U^\top x\), with inverse \(x=U\widehat{x}\). Distinguish measured signals from illustrative test patterns.
- Explain \(x^\top Lx=\tfrac12\sum_{ij}W_{ij}(x_i-x_j)^2=\sum_{\{i,j\}\in E}W_{ij}(x_i-x_j)^2=\sum_k\lambda_k|\widehat{x}_k|^2\), and say which indexing a notebook uses: the ordered-pair sum carries the \(\tfrac12\) and the edge sum does not. Low graph frequency describes variation across edges, not clock time or universally cycles per meter.
- Dirichlet energy carries squared signal units and scales as \(\|x\|^2\), so raw energies are never comparable across signals or across scalings of one signal; normalize by \(x^\top x\) (the Rayleigh quotient) before comparing. For the oriented incidence matrix \(\nabla\), \(L=\nabla^\top\nabla\) and \(x^\top Lx=\|\nabla x\|^2\) — the discrete analogue of \(\int|\nabla f|^2\), which is where the name comes from and where Case Study 5B picks it up.
- Define \(L_{\mathrm{sym}}=I-D^{-1/2}WD^{-1/2}\) for positive-degree nodes; document isolated-node handling and its different degree-scaled smoothness interpretation.
- A large Laplacian weight means strong coupling. Justify converting distance or travel-time cost to affinity; never silently substitute cost for similarity.
- For temporal data, define dimensions and transform conventions explicitly. Separate changing measurements from changing operator weights, and fixed state spaces from fixed operators.
- Distinct graphs can share a spectrum. Eigenvectors have sign and repeated-eigenspace ambiguities; coefficients from different operators are not automatically comparable.

## Notebook implementation and completion

- Prefer Python, NumPy, SciPy, NetworkX, pandas, and Matplotlib. Introduce PyGSP, scikit-learn, GeoPandas, and OSMnx as needed rather than requiring every dependency in Case Study 1.
- Start with small graphs and exact symmetric eigendecomposition. Introduce sparse methods when dataset size warrants them; do not apply symmetric eigensolvers to nonsymmetric matrices.
- Maintain explicit node/edge ordering, consistent plot layouts, random seeds, documented missing-data masks, and clear units. Include source links, access steps, data terms, and dataset/version provenance.
- Clearly label baselines and derived data. Do not present smoothing as validated denoising without an evaluation target; do not treat missing readings as observed zeros.
- Execute every notebook from a fresh kernel through the final cell. Check applicable matrix invariants, eigenpair residuals, component counts, and later GFT inversion and energy preservation.
- Deliver the executed notebook with readable saved outputs and brief environment/run instructions. End with an applied conclusion: what was learned, evidence of usefulness, and remaining limitations.

## Key references

- **[R1]** von Luxburg (2007), [A Tutorial on Spectral Clustering](https://arxiv.org/abs/0711.0189). Foundation for Laplacians, graph cuts, embeddings, and clustering.
- **[R2]** Shuman et al. (2013), [The Emerging Field of Signal Processing on Graphs](https://arxiv.org/abs/1211.0053). Main introduction to graph frequency, the GFT, filtering, and applications.
- **[R3]** Ortega et al. (2018), [Graph Signal Processing: Overview, Challenges and Applications](https://arxiv.org/abs/1712.00468). Broader operator choices, sampling, filtering, and applied uses.
- **[R4]** Schaub and Segarra (2018 preprint), [Flow Smoothing and Denoising: Graph Signal Processing in the Edge-Space](https://arxiv.org/abs/1808.02111). Edge signals, conservation-aware filtering, and a transportation example.
- **[R5]** Grassi et al. (2017 preprint), [A Time-Vertex Signal Processing Framework](https://arxiv.org/abs/1705.02307). Joint graph/time transforms, filtering, and applied demonstrations.
- **[R6]** Li et al. (2018), [Diffusion Convolutional Recurrent Neural Network: Data-Driven Traffic Forecasting](https://arxiv.org/abs/1707.01926). Directed traffic diffusion and the METR-LA/PEMS-BAY context; a related learning application rather than a classical GFT tutorial.
- **[R7]** Gloudemans et al. (2023), [I-24 MOTION: An instrument for freeway traffic science](https://arxiv.org/abs/2301.11198). Trajectory dataset background, measurement process, and transportation context.
- **Implementation:** [NetworkX linear algebra](https://networkx.org/documentation/stable/reference/linalg.html), [PyGSP](https://pygsp.readthedocs.io/en/stable/), and [SciPy sparse linear algebra](https://docs.scipy.org/doc/scipy/reference/sparse.linalg.html).

Verify relevant source details and access requirements when implementing a notebook. Cite original research and official dataset documentation; distinguish proposed curriculum exercises from analyses actually demonstrated in the cited papers.
