%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%% MiniZinc parametric model for FREEDA %%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

include "globals.mzn";

%%%%%%%%%%%%%%%%%%%%%%
%%%%% Parameters %%%%%
%%%%%%%%%%%%%%%%%%%%%%

%%%%% Components and Flavours %%%%%

% All the components.
enum Comps;
% Components that *must* always be deployed.
set of Comps: mustComps;

% All the flavours.
enum Flavs;
% Flav[c] is the set of all flavours offered by component c.
array[Comps] of set of Flavs: Flav;

% CompFlavs is the index set for the rows of the deployment matrices.
set of int: CompFlavs = 1..sum(c in Comps)(length(Flav[c]));
% Idx(c,f) is the row of component c in flavour f in the deployment matrices.
% It maps pairs from Comps × Flavs to indices of CompFlavs.
function int:
Idx(Comps: c, Flavs: f) =
  sum (i in 1..c-1)(length(Flav[Comps[i]])) + arg_max([f = i | i in Flav[c]]);

% Importance of a component in a given flavour.
% FIXME: we assume f ⪯c f′ iff imp(c,f) ≤ imp(c,f′).
array[Comps, Flavs] of int: imp;

% Uses[Idx(c,f),Idx(c',f')] = 1 iff component c in flavour f requires component
% c' in a flavour at least as powerful as f′.
array[CompFlavs, CompFlavs] of 0..1: Uses;

% mayUse[c,Idx(c',f)] = 1 iff c' in flavour f may use c in some flavour.
array[Comps, CompFlavs] of 0..1: mayUse;

%%%%% Resources %%%%%

% Consumable resources.
enum CRes;
% Non-consumable resources.
enum NRes;
% All the resources.
enum Res = C(CRes) ++ N(NRes);

% Req_cf[Idx(c,f)] is the set of resources required by c in flavour f.
array[CompFlavs] of set of Res: Req_cf = [
  {r | r in Res where comReq[cf, r] != worstBounds[r]} | cf in CompFlavs
];

% Req_cfc[c,f,c'] is the set of resources required by the connection between
% "source" component c, deployed in flavour f, and "target" component c′.
array[Comps, Flavs, Comps] of set of Res: Req_cfc = array3d(Comps, Flavs, Comps, 
  [{r | r in Res where depReq[c1, i, c2, r] != worstBounds[r]}
  | c1 in Comps, i in Flavs, c2 in Comps
  ]);

% Lower bound for bestBounds and worseBounds values.
int: MIN_RBOUNDS;
% Upper bound for bestBounds and worseBounds values.
int: MAX_RBOUNDS;
% No value for a resource r can be worse than worstBounds[r].
array[Res] of MIN_RBOUNDS..MAX_RBOUNDS: bestBounds;
% No value for a resource r can be better than bestBounds[r].
array[Res] of MIN_RBOUNDS..MAX_RBOUNDS: worstBounds;

% comReq[Idx(c,f), r] defines the amount of resource r in Req_cf[Idx(c,f)]
% required by c to be executed in flavour f: if worstBounds[r] = MIN_RBOUNDS,
% then c requires at least comReq[Idx(c,f), r] units of r; otherwise, it 
% requires at most comReq[Idx(c,f), r] units of r.
array[CompFlavs, Res] of int: comReq;

% depReq[c, f, c', r] defines the amount of resource r in Req_cfc[c,f,c']
% required by the link connecting the node of the source component c to the
% node of the target component c′: if worstBounds[r] = MIN_RBOUNDS,
% then the link requires at least depReq[c, f, c', r] units of r; otherwise,
% it requires at most depReq[c, f, c', r] units of r.
array[Comps, Flavs, Comps, Res] of int: depReq;

%%%%% Infrastructure, capacity and budget %%%%%

% All the nodes of the infrastructure.
enum Nodes;
% Node 0 is a dummy node added for convenience, to better handle the 
% constraints below. No component can be deployed on node 0.
set of int: Nodes0 = {0} union Nodes;

% Req_n[n] is the set of resources offered by node n.
array[Nodes] of set of Res: Req_n = [
  {r | r in Res where nodeCap[n, r] != worstBounds[r]} | n in Nodes
];

% nodeCap[n,r] is maximum amount of resource r available at node n.
array[Nodes0, Res] of int: nodeCap;
% If n = 0, it must be nodeCap[n,r] = bestBounds[r].
constraint assert (forall(r in Res)(nodeCap[0,r] = bestBounds[r]), 
  "Assertion nodeCap[0,r] = bestBounds[r] failed.", true);

% linkCap[n, n', r] is the maximum amount of r that the link between n and n′
% can handle.
array[Nodes0, Nodes0, Res] of int: linkCap;
% If n = 0 or n' = 0, it must be linkCap[n, n', r] = bestBounds[r].
constraint assert (forall(n in Nodes, r in Res)(
  linkCap[n,0,r] = bestBounds[r] /\ linkCap[0, n, r] = bestBounds[r]),
  "Assertion linkCap[n,0,r] = linkCap[0,n,r] = bestBounds[r] failed.", true);

% cost[n,r] is the unit cost of using resource r node n.
array[Nodes0, Res] of int: cost;
% It must be cost[0,r] = 0.
constraint assert (forall(r in Res)(cost[0,r] = 0), 
  "Assertion cost[0,r] = 0 failed.", true);
% Money budget.
int: costBudget;

% carb[n,r] is the carbon emission per unit of resource r node n.
array[Nodes0, Res] of int: carb;
% It must be carb[0,r] = 0.
constraint assert (forall(r in Res)(carb[0,r] = 0), 
  "Assertion carb[0,r] = 0 failed.", true);
% Carbon budget.
int: carbBudget;


%%%%%%%%%%%%%%%%%%%%%
%%%%% Variables %%%%%
%%%%%%%%%%%%%%%%%%%%%

% D[Idx(c,f),j] = 1 iff component c is deployed in flavour f on node j.
array [{0} union CompFlavs, Nodes0] of var 0..1: D;

% node[c] is the node where c is deployed, or node[c] = 0 if c not deployed.
array [Comps] of var Nodes0: node = [
  sum(i in Flav[c], j in Nodes)(j * D[Idx(c, i), j]) | c in Comps
];

% Total cost of the deployment.
var int: totCost = sum(c in Comps, i in Flav[c], r in Req_cf[Idx(c, i)])(
  comReq[Idx(c, i), r] * cost[node[c], r] * D[Idx(c, i), node[c]]
);

% Total carbon emission of the deployment.
var int: totCarb = sum(c in Comps, i in Flav[c], r in Req_cf[Idx(c, i)])(
  comReq[Idx(c, i), r] * carb[node[c], r] * D[Idx(c, i), node[c]]
);


%%%%%%%%%%%%%%%%%%%%%%%
%%%%% Constraints %%%%%
%%%%%%%%%%%%%%%%%%%%%%%

% Zero values for D[0,j] and D[i,0].
constraint forall(j in Nodes0)(D[0, j] = 0);
constraint forall(i in CompFlavs)(D[i, 0] = 0);

% Each component is deployed in at most one flavour, on at most one node.
constraint forall(c in Comps)(
  sum(i in Flav[c], j in Nodes)(D[Idx(c, i), j]) <= 1
);

% Components that must be deployed
constraint forall(m in mustComps)(
  sum (i in Flav[m], j in Nodes)(D[Idx(m, i), j]) > 0 /\ node[m] > 0
);

% If component c is deployed in flavour i, for each (c',i') in Uses[c,i]
% component c' must be deployed in a flavour bigger or equal than i'.
constraint forall(
  c in Comps,
  i in Flav[c],
  cu in Comps,
  iu in Flav[cu] where Uses[Idx(c, i), Idx(cu, iu)] = 1
)(
  sum(j in Nodes)(D[Idx(c, i), j]) <= 
  sum(k in Flav[cu], j in Nodes where imp[cu,k] >= imp[cu,iu])(D[Idx(cu, k),j])
);

% If a "target" component c not in mustComps is deployed, at least one "source"
% component c' must be deployed in a flavour f requiring c.
constraint forall(c in Comps diff mustComps)(
  sum(i in Flav[c], j in Nodes)(D[Idx(c, i), j]) <= 
  sum(cs in Comps where c != cs,
      is in Flav[cs] where mayUse[c, Idx(cs, is)] = 1, j in Nodes)
      ( D[Idx(cs, is), j] )
);

% Each node j has a sufficient quantity of a certain resource r to meet the
% demands of all the components deployed on it.
constraint forall(j in Nodes, r in Req_n[j] where r in CRes) (
  if worstBounds[r] = MIN_RBOUNDS then
    sum(c in Comps, i in Flav[c] where r in Req_cf[Idx(c,i)])
      (comReq[Idx(c,i), r] * D[Idx(c,i), j]) <= nodeCap[j,r]
  else
    sum(c in Comps, i in Flav[c] where r in Req_cf[Idx(c,i)])
      (comReq[Idx(c,i), r] * D[Idx(c,i), j]) >= nodeCap[j,r]
  endif
);

% If component c deployed in flavour i requires a certain amount of resource r,
% then node c must have capacity for r
constraint forall(c in Comps, i in Flav[c], r in Req_cf[Idx(c,i)])(
  if worstBounds[r] = MIN_RBOUNDS then
    comReq[Idx(c,i), r] * D[Idx(c,i), node[c]] <= nodeCap[node[c], r]
  else
    comReq[Idx(c,i), r] * D[Idx(c,i), node[c]] >= nodeCap[node[c], r]
  endif
);

% Dependency from c to c' must be fulfilled only if there is an active
% dependency between c and c'.
constraint forall(
  cd in Comps,
  cs in Comps,
  is in Flav[cs],
  r in Req_cfc[cs, is, cd] where r in NRes
)(
  depReq[cs, is, cd, r] * sum(j in Nodes)(D[Idx(cs, is), j]) <= 
  linkCap[node[cs], node[cd], r]
);

% Budget requirements.
constraint totCost <= costBudget;
constraint totCarb <= carbBudget;


%%%%%%%%%%%%%%%%%%%%%
%%%%% Objective %%%%%
%%%%%%%%%%%%%%%%%%%%%

% ------- Objective function that maximizes flavour importance ------
% var int: obj = sum(c in Comps, i in Flav[c])(
%   imp[c,i] * sum([D[Idx(c,i),j] | j in Nodes])
% );
% % solve maximize obj;

% ------- Objective function that minimizes cost ------
array[Nodes] of var 0..1: u;
constraint forall(j in Nodes, c in Comps, i in Flav[c])(u[j] >= D[Idx(c, i), j]);
constraint forall(j in Nodes)(u[j] <= sum(c in Comps, i in Flav[c])(D[Idx(c, i), j]));

% array[Nodes] of
% MIN_RBOUNDS*min(cost)
% ..
% sum(r in Res, j in Nodes0)(nodeCap[j, r] * cost[j, r]):
% w = [
%   sum(r in Res)(nodeCap[j, r] * cost[j, r])
%   | j in Nodes
% ];

% var int: obj = sum(j in Nodes)(w[j]*u[j]);
var int: obj = sum(j in Nodes, r in Res)(cost[j, r]*u[j]);

solve minimize obj;


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%% Output formatting %%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

output [
  let {
    var int: deployed_amount = sum(c in Comps)(node[c] = n),
    set of int: amount = 1..fix(deployed_amount),
    array[amount] of Comps: deployed = [c | c in Comps where fix(node[c]) = n],
    array[amount] of Flavs: flav_deployed = [f | c in deployed, f in Flav[c] where fix(D[Idx(c, f), n]) = 1]
  } in
  concat(
    ["\(n): \n"] ++ [
      " - [\(cd), \([f | f in Flav[cd], fd in flav_deployed where D[Idx(cd, fd), n] = 1][1])]\n"
      | cd in deployed
    ]
  )
  | n in Nodes
];
