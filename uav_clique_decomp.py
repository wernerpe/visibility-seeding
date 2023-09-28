import numpy as np
from uav_boxes import Village
from seeding_utils import point_near_regions, vis_reg, point_in_regions
from scipy.sparse import lil_matrix
import numpy as np
from tqdm import tqdm
from region_generation import generate_regions_multi_threading

seed = 0
#alpha = 0.05
eps = 0.2
approach = 1
N = 500
ap_names = ['redu', 'greedy', 'nx', 'greedy_edge_CC', 'greedy_cvx_hull_fill']

for seed in range(0,1):
    world = Village()
    village_side = 39
    village_height = 10
    world.build(village_height=village_height, village_side=village_side, building_every=5, density=0.15, seed=seed)
    #vgraph_builder = world.to_drake_plant()
    print(len(world.obstacles))


    def sample_cfree_handle(n, m, regions=None):
        points = np.zeros((n,3))
        m = m*100
        if regions is None: regions = []		
        for i in range(n):
            bt_tries = 0
            while bt_tries<m:
                point = world.sample_cfree(1)[0]
                #point = world.sample_cfree(1)[0]
                if point_near_regions(point, regions, tries = 5, eps = 0.1):
                    bt_tries+=1
                else:
                    break
            # if bt_tries == m:
            #     return points, True
            points[i] = point
        return points, False

    def estimate_coverage(regions):
        n_s = 5000
        samples = world.sample_cfree(n_s)
        in_s = 0
        for s in samples:
            if point_in_regions(s, regions):
                in_s+=1
        return (1.0*in_s)/n_s

    from vislogging import LoggerClique3D
    from visibility_clique_decomposition import VisCliqueDecomp
    from region_generation import generate_regions_ellipses_multi_threading
    from time import strftime,gmtime
    from functools import partial


    loggerccd = LoggerClique3D(world, f"village_{ap_names[approach]}_{village_side}_{village_height}_"+strftime("%m_%d_%H_%M_%S_", gmtime())+"_", seed, N, alpha, eps, estimate_coverage)
    def iris_ellipse_w_obstacles_handle(points, ellipsoids, old_regions = None):
        if len(points)>=1:
            #+ region_obstacles
            obstacles = [r for r in world.obstacles]
            regions, _, is_full = generate_regions_ellipses_multi_threading(points, ellipsoids, obstacles, world.iris_domain, estimate_coverage, coverage_threshold=1-eps, old_regs = old_regions, maxiters=1)
        return regions, is_full
    
    VCD = VisCliqueDecomp(  N = N,
                            eps = eps,
                            max_iterations=300,
                            sample_cfree=sample_cfree_handle,
                            col_handle= world.col_handle,
                            build_vgraph= world.vgraph_handle,
                            iris_w_obstacles= iris_ellipse_w_obstacles_handle,
                            verbose=True,
                            logger=loggerccd, 
                            approach = approach,
                        )

    VCD.run()