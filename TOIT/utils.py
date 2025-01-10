import random, re, itertools

def for_with_join(preamble, content, n):
    return preamble + "\n" + "\n".join(content for _ in range(n)) + "\n]);\n\n"

def generate(**kwargs):
    frontends = ["frontend" + str(i) for i in range(random.randint(2, 3))]
    backends = ["backend" + str(i) for i in range(random.randint(2, 3))]
    databases = ["database" + str(i) for i in range(random.randint(2, 2))]
    nodes = ["n" + str(i) for i in range(1, random.randint(4, 5))]

    components = frontends + backends + databases
    must_components = frontends

    compFlavs_len = len(frontends) * 2 + len(backends) * 3 + len(databases)

    result = "Comps = {" + ", ".join(components) + "};\n"
    result += "mustComps = {" + ", ".join(must_components) + "};\n"
    result += "Flavs = {tiny, medium, large};\n"
    result += "Nodes = {" + ", ".join(nodes) + "};\n"
    result += "CRes = {CPU, RAM, storage, bwIn, bwOut};\n"
    result += "NRes = {ssl, fwall, encr, avail, latency};\n"
    result += ("Flav = [" +
        ", ".join("{medium, large}" for _ in frontends) + ", " +
        ", ".join("{tiny, medium, large}" for _ in backends) + ", " +
        ", ".join("{large}" for _ in databases) +
    "];\n")

    frontend_compFlavs = list(itertools.product(frontends, ["medium", "large"]))
    backend_compFlavs = list(itertools.product(backends, ["tiny", "medium", "large"]))
    databases_compFlavs = list(itertools.product(databases, ["large"]))
    compFlavs = frontend_compFlavs + backend_compFlavs + databases_compFlavs

    uses = []
    for f in frontends:
        b = random.choices(backends)[0]
        uses += [
            (f, "medium", b, "tiny"),
            (f, "large", b, "tiny")
        ]
    for b in backends:
        d = random.choices(backends)[0]
        uses += [
            (b, "medium", d, "large"),
            (b, "large", d, "large")
        ]

    result += "Uses = array2d(CompFlavs, CompFlavs, [\n\t" + "\n\t".join(
        ",".join(
            str(1 if (c1, f1, c2, f2) in uses else 0)
            for c2, f2 in compFlavs
        ) + ","
        for c1, f1 in compFlavs
    ) + "\n]);\n"

    uses_no_end_flav = [(cf, ff, ct) for cf, ff, ct, _ in uses]
    result += "mayUse = array2d(Comps, CompFlavs, [\n\t" + "\n\t".join(
        ",".join(
            str(1 if (c2, f2, c1) in uses_no_end_flav else 0)
            for c2, f2 in compFlavs
        ) + ","
        for c1 in components
    ) + "\n]);\n"

    result += "MIN_RBOUNDS = 0;\n"
    result += "MAX_RBOUNDS = 1000000;\n\n"

    result += "worstBounds = [0, 0, 0, 0, 0, 0, 0, 0, 0, MAX_RBOUNDS];\n"
    result += "bestBounds = [MAX_RBOUNDS - i | i in worstBounds];\n\n"

    result += for_with_join(
        "comReq = array2d(CompFlavs, Res, [",
        "  T_CPU_COM, T_RAM_COM, T_STORAGE_COM, T_BWIN_COM, T_BWOUT_COM, T_SSL, T_FW, T_ENCR, T_AVAIL_COM, MAX_RBOUNDS,",
        compFlavs_len
    )
    result += for_with_join(
        "nodeCap = array2d(Nodes0, Res, [bestBounds[r] | r in Res] ++ [",
        "  T_NODE_CPU, T_RAM_NODE, T_STORAGE_NODE, T_BWIN_NODE, T_BWOUT_NODE, T_SSL_NODE, T_FW_NODE, T_ENCR_NODE, T_AVAIL_NODE, 0,",
        len(nodes)
    )
    result += for_with_join(
        "cost = array2d(Nodes0, Res, [\n  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, % no node",
        "  T_COST_CPU, T_COST_RAM, T_COST_STORAGE, 0, 0, 0, 0, 0, 0, 0,",
        len(nodes)
    )
    result += for_with_join(
        "carb = array2d(Nodes0, Res, [\n  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, % no node",
        "  T_CONS, T_CONS, T_CONS, 0, 0, 0, 0, 0, 0, 0,",
        len(nodes)
    )

    result += "costBudget = T_B_COST;\n"
    result += "carbBudget = T_B_CONS;\n\n"

    result += "depReq = array4d(Comps, Flavs, Comps, Res, [\n"
    how_many_depReq = max(len(frontends), len(backends)) ** 3
    random_array_1 = random.choices(frontends, k=how_many_depReq)
    random_array_2 = random.choices(backends, k=how_many_depReq)
    body = "\n".join(list(set([
        f"  elseif c1 = {e1} /\ c2 = {e2} /\ r = N(avail) then\n    T_AVAIL_COM" # avail only
        for e1, e2 in zip(random_array_1, random_array_2)
        if e1 != e2
    ])))
    body = "  " + body[6:] # remove the first else making it just a if
    body += "\n  else\n    worstBounds[r]\n" # add final else
    body += "  endif | c1 in Comps, i in Flavs, c2 in Comps, r in Res" # add final condition
    result += body + "]);\n\n"

    result += "linkCap = array3d(Nodes0, Nodes0, Res, [\n"
    result += "  if ni = 0 \/ nj = 0 then\n    bestBounds[r]\n"
    result += "  elseif ni = nj /\ r = N(avail) then\n    nodeCap[ni,r]\n"
    how_many_nodes = max(len(nodes), len(nodes)) ** 3
    random_array_1 = random.choices(nodes, k=how_many_nodes)
    random_array_2 = random.choices(nodes, k=how_many_nodes)
    random_tuples = {(e1, e2) for e1, e2 in zip(random_array_1, random_array_2) if e1 != e2}
    random_tuples = set(map(tuple, map(sorted, random_tuples)))
    body = "\n".join([
        "  elseif {ni, nj} = {" + e1 + ", " + e2 + "} /\ r = N(avail) then\n    T_AVAIL_NODE" # avail only
        for e1, e2 in random_tuples
    ])
    body += "\n  else\n    worstBounds[r]\n" # add final else
    body += "  endif | ni in Nodes0, nj in Nodes0, r in Res" # add final condition
    result += body + "]);\n\n"

    to_sub = {
        "T_CPU_COM" : lambda _ : str(random.choices([2, 4, 8], [0.7, 0.2, 0.1])[0]),
        "T_SSL_NODE" : lambda _ : str(random.choices([0, 1], [0.1, 0.9])[0]),
        "T_SSL" : lambda _ : str(random.choices([0, 1], [0.3, 0.7])[0]),
        "T_ENCR_NODE" : lambda _ : str(random.choices([0, 1], [0.1, 0.9])[0]),
        "T_ENCR" : lambda _ : str(random.choices([0, 1], [0.4, 0.6])[0]),
        "T_FW_NODE" : lambda _ : str(random.choices([0, 1], [0.2, 0.8])[0]),
        "T_FW" : lambda _ : str(random.choices([0, 1], [0.4, 0.6])[0]),
        "T_CONS" : lambda _ : str(random.randint(1, 50)),
        "T_COST_CPU" : lambda _ : str(random.randint(10, 20)),
        "T_COST_RAM" : lambda _ : str(random.randint(5, 10)),
        "T_COST_STORAGE" : lambda _ : str(random.randint(15, 25)),
        "T_NODE_CPU" : lambda _ : str(random.choices([8, 16, 32], [0.1, 0.5, 0.4])[0]),
        "T_STORAGE_NODE" : lambda _ : str(random.randint(30_000, 1_000_000)),
        "T_STORAGE_COM" : lambda _ : str(random.randint(200, 500)),
        "T_RAM_NODE" : lambda _ : str(random.randint(16_000, 128_000)),
        "T_RAM_COM" : lambda _ : str(random.randint(200, 500)),
        "T_BWIN_NODE" : lambda _ : str(random.randint(10_000, 25_000)),
        "T_BWIN_COM" : lambda _ : str(random.randint(200, 1000)),
        "T_BWOUT_NODE" : lambda _ : str(random.randint(10_000, 25_000)),
        "T_BWOUT_COM" : lambda _ : str(random.randint(200, 1000)),
        "T_AVAIL_NODE" : lambda _ : str(random.randint(98, 99)),
        "T_AVAIL_COM" : lambda _ : str(random.randint(95, 97)),

        "T_B_CONS" : lambda _ : str(random.randint(5_000 * len(components), 10_000 * len(components))),
        "T_B_COST" : lambda _ : str(random.randint(5_000 * len(components), 10_000 * len(components))),
    }

    for keyword, substitution in to_sub.items():
        result = re.sub(keyword, substitution, result)

    result += "imp = array2d(Comps, Flavs, [\n"
    for _ in components:
        imps = sorted(random.sample(range(1, 10), 3))
        result += "  " + ", ".join(str(a) for a in imps) + ",\n"
    result += "]);\n\n"

    return result
