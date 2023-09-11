from independent_set_solver import solve_max_independent_set_integer
from ellipse_utils import get_lj_ellipse
from pydrake.all import Hyperellipsoid
import numpy as np
import networkx as nx
import subprocess

def networkx_to_metis_format(graph):
    num_nodes = graph.number_of_nodes()
    num_edges = graph.number_of_edges()

    metis_lines = [f"{num_nodes} {num_edges} {0}\n"]
    
    for node in range(num_nodes):
        neighbors = " ".join(str(neighbor + 1) for neighbor in graph.neighbors(node))
        metis_lines.append(neighbors + "\n")
    
    return metis_lines


def compute_cliques_REDUVCC(ad_mat, maxtime = 30):
    nx_graph = nx.Graph(ad_mat)
    metis_lines = networkx_to_metis_format(nx_graph)
    edges = 0
    for i in range(ad_mat.shape[0]):
        #for j in range(i+1, ad_mat.shape[0]):
        edges+=np.sum(ad_mat[i, i+1:])    
    with open("tmp/vgraph.metis", "w") as f:
        f.writelines(metis_lines)
        f.flush()  # Flush the buffer to ensure data is written immediately
        f.close()
    binary_loc = "/home/peter/git/ExtensionCC_test/ExtensionCC/out/optimized/vcc "
    options = f"--solver_time_limit={maxtime} --seed=5 --run_type=ReduVCC --output_cover_file=tmp/cliques.txt "
    file = "tmp/vgraph.metis"
    command = binary_loc + options + file
    p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)

    (output, err) = p.communicate()
    print(str(str(output)[2:-1]).replace('\\n', '\n '))
    with open("tmp/cliques.txt", "r") as f:
        cliques_1_index = f.readlines()
    cliques_1_index = [c.split(' ') for c in cliques_1_index]
    cliques = [np.array([int(c)-1 for c in cli]) for cli in cliques_1_index]
    cliques = sorted(cliques, key=len)[::-1]
    return cliques

def compute_greedy_clique_partition(adj_mat):
    cliques = []
    done = False
    adj_curr = adj_mat.copy()
    adj_curr = 1- adj_curr
    np.fill_diagonal(adj_curr, 0)
    ind_curr = np.arange(len(adj_curr))
    while not done:
        val, ind_max_clique_local = solve_max_independent_set_integer(adj_curr)
        #non_max_ind_local = np.arange(len(adj_curr))
        #non_max_ind_local = np.delete(non_max_ind_local, ind_max_clique_local, None)
        index_max_clique_global = np.array([ind_curr[i] for i in ind_max_clique_local])
        cliques.append(index_max_clique_global.reshape(-1))
        adj_curr = np.delete(adj_curr, ind_max_clique_local, 0)
        adj_curr = np.delete(adj_curr, ind_max_clique_local, 1)
        ind_curr = np.delete(ind_curr, ind_max_clique_local)
        if len(adj_curr) == 0:
            done = True
    return cliques

from pydrake.all import MathematicalProgram, SolverOptions, Solve, CommonSolverOption

def solve_max_edge_clique_integer(adj_mat, M):
    n = adj_mat.shape[0]
    assert M.shape[0] == M.shape[1] and M.shape[0] ==n and np.max(M-M.T) ==0 and np.max(M.diagonal()) == 0
    J = np.ones(M.shape)
    if n == 1:
        return 1, np.array([0])
    prog = MathematicalProgram()
    v = prog.NewBinaryVariables(n)
    prog.AddQuadraticCost(-0.5*(v.T@(J-M)@v - np.sum(v)), is_convex=True)
    for i in range(0,n):
        for j in range(i+1,n):
            if adj_mat[i,j] == 0:
                prog.AddLinearConstraint(v[i] + v[j] <= 1)

    solver_options = SolverOptions()
    solver_options.SetOption(CommonSolverOption.kPrintToConsole, 1)

    result = Solve(prog, solver_options=solver_options)
    return -result.get_optimal_cost(), np.nonzero(result.GetSolution(v))[0]

def compute_greedy_edge_clique_cover(adj_mat):
    cliques = []
    done = False
    adj_curr = adj_mat.copy()
    ind_curr = np.arange(len(adj_curr))
    M = np.zeros(adj_mat.shape)
    M_loc = np.zeros(adj_mat.shape)
    while not done:
        val, ind_max_clique_local = solve_max_edge_clique_integer(adj_curr, M_loc)
        #non_max_ind_local = np.arange(len(adj_curr))
        #non_max_ind_local = np.delete(non_max_ind_local, ind_max_clique_local, None)
        for idx, i in enumerate(ind_max_clique_local[:-1]):
            for j in ind_max_clique_local[idx+1:]:
                M_loc[i,j] = 1
                M_loc[j,i] = 1
                #debug
                i_glob = ind_curr[i]
                j_glob = ind_curr[j]
                M[i_glob,j_glob] = 1
                M[j_glob,i_glob] = 1

        index_max_clique_global = np.array([ind_curr[i] for i in ind_max_clique_local])
        cliques.append(index_max_clique_global.reshape(-1))

        idx_local_to_remove = []
        for i in range(M_loc.shape[0]):
            # all edges have been covered
            if ~np.any(M_loc[i, :] - adj_curr[i,  :]):
                idx_local_to_remove.append(i)
        idx_local_to_remove = np.array(idx_local_to_remove)
        adj_curr = np.delete(adj_curr, idx_local_to_remove, 0)
        adj_curr = np.delete(adj_curr, idx_local_to_remove, 1)
        M_loc = np.delete(M_loc, idx_local_to_remove, 0)
        M_loc = np.delete(M_loc, idx_local_to_remove, 1)
        ind_curr = np.delete(ind_curr, idx_local_to_remove)
        if len(adj_curr) == 0:
            done = True
    return cliques, M

# def solve_max_clique_cvx_hull(adj_mat, containment_points,):
#     n = adj_mat.shape[0]
#     assert M.shape[0] == M.shape[1] and M.shape[0] ==n and np.max(M-M.T) ==0 and np.max(M.diagonal()) == 0
#     J = np.ones(M.shape)
#     if n == 1:
#         return 1, np.array([0])
#     prog = MathematicalProgram()
#     v = prog.NewBinaryVariables(n)
#     prog.AddQuadraticCost(-0.5*(v.T@(J-M)@v - np.sum(v)), is_convex=True)
#     for i in range(0,n):
#         for j in range(i+1,n):
#             if adj_mat[i,j] == 0:
#                 prog.AddLinearConstraint(v[i] + v[j] <= 1)

#     solver_options = SolverOptions()
#     solver_options.SetOption(CommonSolverOption.kPrintToConsole, 1)

#     result = Solve(prog, solver_options=solver_options)
#     return -result.get_optimal_cost(), np.nonzero(result.GetSolution(v))[0]

# def compute_greedy_clique_partition_convex_hull_constraint(adj_mat, points_vgraph, collision_points):


def compute_minimal_clique_partition_nx(adj_mat):
    n = len(adj_mat)

    adj_compl = 1- adj_mat
    np.fill_diagonal(adj_compl, 0)
    graph = nx.Graph(adj_compl)
    sol = nx.greedy_color(graph, strategy='largest_first', interchange=True)

    colors= [sol[i] for i in range(n)]
    unique_colors = list(set(colors))
    cliques = []
    nr_cliques = len(unique_colors)
    for col in unique_colors:
        cliques.append(np.where(np.array(colors) == col)[0])
    return cliques

def get_iris_metrics(cliques, collision_handle):
    seed_ellipses = [get_lj_ellipse(k) for k in cliques]
    seed_points = []
    for k,se in zip(cliques, seed_ellipses):
        center = se.center()
        dim = len(se.center())
        if not collision_handle(center):
            distances = np.linalg.norm(np.array(k).reshape(-1,dim) - center, axis = 1).reshape(-1)
            mindist_idx = np.argmin(distances)
            seed_points.append(k[mindist_idx])
        else:
            seed_points.append(center)

    #rescale seed_ellipses
    mean_eig_scaling = 1000
    seed_ellipses_scaled = []
    for e in seed_ellipses:
        eigs, _ = np.linalg.eig(e.A())
        mean_eig_size = np.mean(eigs)
        seed_ellipses_scaled.append(Hyperellipsoid(e.A()*(mean_eig_scaling/mean_eig_size), e.center()))
    #sort by size
    #idxs = np.argsort([s.Volume() for s in seed_ellipses])[::-1]
    hs = seed_points#[seed_points[i] for i in idxs]
    se = seed_ellipses_scaled #[seed_ellipses_scaled[i] for i in idxs]
    return hs, se