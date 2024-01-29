# -*- coding: utf-8 -*-
"""
Created on Sun Jan 28 16:38:55 2024

@author: udu
"""

# Import required modules
import os
import sys
import openseespy.opensees as ops
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.ticker import StrMethodFormatter

# Append directory of helper functions to Pyhton Path
sys.path.append('../')

from helper_functions.create_floor_shell import refine_mesh
from helper_functions.create_floor_shell import create_shell
from helper_functions.build_smf_column import create_columns
from helper_functions.build_smf_beam import create_beams
from helper_functions.create_regions import create_beam_region, create_column_region

from helper_functions.eigen_analysis import run_eigen_analysis

from helper_functions.set_recorders import create_beam_recorders, create_column_recorders
from helper_functions.run_mrsa import perform_mrsa

from helper_functions.get_beam_col_demands import process_beam_col_resp
from helper_functions.get_story_drift import compute_story_drifts
from helper_functions.cqc_modal_combo import modal_combo
from helper_functions.elf_new_zealand import nz_horiz_seismic_shear, nz_horiz_force_distribution
from helper_functions.get_spectral_shape_factor import spectral_shape_fac

# Set plotting parameters
mpl.rcParams['axes.edgecolor'] = 'grey'
mpl.rcParams['lines.markeredgewidth'] = 0.4
mpl.rcParams['lines.markeredgecolor'] = 'k'
plt.rcParams.update({'font.family': 'Times New Roman'})

axes_font = {'family': "sans-serif",
              'color': 'black',
              'size': 8
              }

title_font = {'family': 'sans-serif',
              'color': 'black',
              'weight': 'bold',
              'size': 8}

legend_font = {'family': 'Times New Roman',
              'size': 8}

# Define Units
sec = 1

# US units
inch = 1
kips = 1

ft = 12 * inch
lb = kips/1000
ksi = kips/inch**2
psi = ksi/1000
grav_US = 386.4 * inch/sec**2

# Metric Units
m = 1
kN  = 1

mm = m / 1000
N = kN/1000
kPa = 0.001 * N/mm**2   # Kilopascal
MPa = 1 * N/mm**2       # Megapascal
GPa = 1000 * N/mm**2    # Gigapascal
grav_metric = 9.81 * m/sec**2

print('Basic units are: \n \t Force: kN; \n \t Length: m; \n \t Time: sec.')
print('')

# Floor elevations
typ_flr_height = 3.1 * m
ground_flr = 0.0 * m

flr1 = 4.5 * m
flr2 = flr1 + typ_flr_height
flr3 = flr2 + typ_flr_height
flr4 = flr3 + typ_flr_height
flr5 = flr4 + typ_flr_height
flr6 = flr5 + typ_flr_height
flr7 = flr6 + typ_flr_height
flr8 = flr7 + typ_flr_height
flr9 = flr8 + typ_flr_height
flr10 = flr9 + typ_flr_height
roof_flr = flr10 + typ_flr_height

story_heights = np.array([flr1, typ_flr_height, typ_flr_height, typ_flr_height, typ_flr_height, typ_flr_height,
                 typ_flr_height, typ_flr_height, typ_flr_height, typ_flr_height, typ_flr_height]) # Story heights from Floor 1 to Roof

elev = [flr1, flr2, flr3, flr4, flr5, flr6, flr7, flr8, flr9, flr10, roof_flr]

# Column centerline x-y coordinates in meters
ssmf_cols_coord_dict = {'col1': [0, 0],
                   'col2': [6.505, 0],
                   'col3': [13.010, 0],
                   'col4': [21.210, 0],
                   'col5': [29.410, 0],
                   'col6': [0., 2.225],
                   'col7': [29.410, 2.225],
                   'col8': [0, 9.425],
                   'col9': [6.505, 9.425],
                   'col10': [13.010, 9.425],
                   'col11': [21.210, 9.425],
                   'col12': [29.410, 9.425],
                   'col13': [0, 16.625],
                   'col14': [6.505, 16.625],
                   'col15': [13.010, 16.625],
                   'col16': [21.210, 16.625],
                   'col17': [29.410, 16.625],
                   'col18': [13.010, 23.825],
                   'col19': [21.210, 23.825],
                   'col20': [29.410, 23.825],
                   'col21': [13.010, 31.025],
                   'col22': [21.210, 31.025],
                   'col23': [29.410, 31.025]}

ssmf_cols_coord_df = pd.DataFrame.from_dict(ssmf_cols_coord_dict, orient='index', columns=['x', 'y'])

# Create a dataframe to store node tags nodes at column locations.
ssmf_cols_node_tags = pd.DataFrame(columns=['00', '01', '02', '03', '04', '05',
                                       '06', '07', '08', '09', '10', '11'],
                             index=ssmf_cols_coord_df.index)

'Sort x and y-coordinates of SMF. This will be used to define a mesh grid'
# Extract x & y coordinates, sort and remove dupllicates
col_x_coords = sorted(list(set([coord for coord in ssmf_cols_coord_df['x']])))
col_y_coords = sorted(list(set([coord for coord in ssmf_cols_coord_df['y']])))

col_x_coords = np.array(list(col_x_coords))
col_y_coords = np.array(list(col_y_coords))

# Create mesh
discretize = 0
if discretize:
    mesh_size = 4 * m  # Mesh size - 4m x 4m elements
    x_coords = refine_mesh(col_x_coords, mesh_size)
    y_coords = refine_mesh(col_y_coords, mesh_size)
else:
    x_coords = col_x_coords
    y_coords = col_y_coords


# Generated mesh grid covers the full rectangular area, trim grid to account for actual building plan
ylim = 16.625  # y-limit of reentrant corner
xlim = 13.010  # x-limit of reentrant corner

mesh_grid_df = pd.DataFrame(columns=['x', 'y'])

row = 0

for x in x_coords:
    for y in y_coords:

        if not((x < xlim) and (y > ylim)):
            mesh_grid_df.loc[row] = [x, y]
            row += 1

mesh_grid_df = mesh_grid_df.round(decimals = 4)

# Extract unique y-coordinate values
unique_ys = mesh_grid_df.y.unique()
num_y_groups = len(unique_ys)

# Group x-coordinates based on y-coordinate value
grouped_x_coord = []

row = 0
for val in unique_ys:
    grouped_x_coord.append(np.array(mesh_grid_df[mesh_grid_df.y == val].x))

# ============================================================================
# Load in New Zealand steel section database
# ============================================================================
nzs_beams = pd.read_excel('../../../nzs_steel_database.xlsx', sheet_name='Beams',
                               index_col='Designation')

nzs_cols = pd.read_excel('../../../nzs_steel_database.xlsx', sheet_name='Columns',
                               index_col='Designation')

nzs_cols = pd.concat([nzs_cols, nzs_beams])

# ============================================================================
# Define shell properties for floor diaphragm
# ============================================================================
nD_mattag = 1
plate_fiber_tag = 2
shell_sect_tag = 1

slab_thick = 165 * mm
fiber_thick = slab_thick / 3

shell_E =  26000 * MPa # Modulus of concrete
shell_nu = 0.2  # Poisson's ratio

# ============================================================================
# Define generic steel properties
# ============================================================================
steel_E = 210 * GPa
steel_Fy = 300 * MPa  # Using AS/NZS 3679.1-300 SO (SEISMIC) steel

# ============================================================================
# Define rigid material for beam-column joints elements in panel zone region
# ============================================================================
pzone_transf_tag_col = 100
pzone_transf_tag_bm_x = 200
pzone_transf_tag_bm_y = 300

# ============================================================================
# Define beam properties
# ============================================================================
bm_nu = 0.28  # Poisson's ratio for steel
bm_E = steel_E
bm_G = bm_E / (2*(1 + bm_nu))

bm_transf_tag_x = 3  # Beams oriented in Global-X direction
bm_transf_tag_y = 4  # Beams oriented in Global-Y direction

# ============================================================================
# Define column properties
# ============================================================================
col_nu = 0.28  # Poisson's ratio for steel
col_E = steel_E
col_G = col_E / (2*(1 + col_nu))

col_transf_tag_EW = 1
col_transf_tag_NS = 2

col_beam_mom_ratio = 1.25
ductility_factor = 4.0  # SMF Category 1 structure (Basically response modification R & deflection amplification Cd factoor)

# ============================================================================
# Initialize dictionary to store node tags of COM for all floors
# Initialize dictionary to store total mass of each floor
# ============================================================================
com_node_tags = {}
total_floor_mass = {}

# Eigen analysis parameters
num_modes = 10
damping_ratio = 0.05

# Drift amplification factor
drift_modif_fac = 1.5  # NZS 1170.5-2004: Table 7.1

# ============================================================================
# Define function to create a floor
# ============================================================================
def create_floor(elev, floor_num, not_for_optimization, beam_prop=None, col_prop=None, floor_label=''):

    node_compile = []  # Store node numbers grouped according to their y-coordinates

    # Initialize node tag for bottom-left node
    node_num = int(floor_num + '1000')

    # Create nodes
    for jj in range(len(unique_ys)):
        x_vals = grouped_x_coord[jj]
        node_list = []

        for x_val in x_vals:

            if floor_num == '00': # Only create bottom floor nodes at the location of columns

                # Check if the current node is at the location of a column
                if (ssmf_cols_coord_df == [x_val, unique_ys[jj]]).all(1).any():

                    ops.node(node_num, x_val, unique_ys[jj], elev)

                    # Assign Boundary conditions
                    ops.fix(node_num, 1, 1, 1, 1, 1, 1)

            else:
                ops.node(node_num, x_val, unique_ys[jj], elev)

            'Store node tags for nodes at the location of columns'
            # Check if the current node is at the location of an SSMF column
            if (ssmf_cols_coord_df == [x_val, unique_ys[jj]]).all(1).any():

                # Get the row index
                row_id = ssmf_cols_coord_df[(ssmf_cols_coord_df['x'] == x_val) & (ssmf_cols_coord_df['y'] == unique_ys[jj])].index.tolist()[0]

                # Assign node tag to `ssmf_cols_coord_df`
                ssmf_cols_node_tags.loc[row_id][floor_num] = node_num

                # Create additional nodes for rigid column elements in panel zone region
                # Along column line
                if floor_num != '00':

                    bm_col_joint_node_top = int(str(node_num) + '1')
                    bm_col_joint_node_bot = int(str(node_num) + '2')

                    pz_d = beam_prop[0]['d'] / 2 * mm # Half the depth of panel zone region
                    ops.node(bm_col_joint_node_bot, x_val, unique_ys[jj], elev - pz_d)

                    if floor_num != '11':  # No panel zone above roof level
                        ops.node(bm_col_joint_node_top, x_val, unique_ys[jj], elev + pz_d)

            # Move to next node
            node_list.append(node_num)
            node_num += 1

        node_compile.append(node_list)

    # Store node tag for COM node
    com_node = node_num # Node tag assigned to center of mass for the current floor.

    # Get all node tags in current floor
    floor_node_tags = [node for node_list in node_compile for node in node_list]

    # ========================================================================
    # Create floor diaphragm - Loads & mass are assigned here
    # Compute center of mass
    # Then create columns and beams
    # ========================================================================
    if floor_num != '00':

        # Create shell - Assign loads & mass
        create_shell(floor_num, node_compile, shell_sect_tag, num_y_groups)

        # Compute center of mass
        floor_node_x_coord = [ops.nodeCoord(node, 1) for node in floor_node_tags]
        floor_node_y_coord = [ops.nodeCoord(node, 2) for node in floor_node_tags]

        floor_node_x_mass = [ops.nodeMass(node, 1) for node in floor_node_tags]
        floor_node_y_mass = [ops.nodeMass(node, 2) for node in floor_node_tags]

        # Store total floor mass
        total_floor_mass[floor_num] = round(sum(floor_node_x_mass), 3)

        # Initialize DataFrame to store nodal data for COM computation
        com_data = pd.DataFrame()

        com_data['NodeTags'] = floor_node_tags
        com_data['xCoord'] = floor_node_x_coord
        com_data['yCoord'] = floor_node_y_coord
        com_data['xMass'] = floor_node_x_mass
        com_data['yMass'] = floor_node_y_mass

        com_data['xMass_xCoord'] = com_data['xMass'] * com_data['xCoord']
        com_data['yMass_yCoord'] = com_data['yMass'] * com_data['yCoord']

        com_x = com_data['xMass_xCoord'].sum() / com_data['xMass'].sum()
        com_y = com_data['yMass_yCoord'].sum() / com_data['yMass'].sum()

        # Create COM node
        ops.node(com_node, com_x, com_y, elev)

        # Impose rigid diaphragm constraint
        ops.rigidDiaphragm(3, com_node, *floor_node_tags)

        # Constraints for Rigid Diaphragm Primary node
        ops.fix(com_node, 0, 0, 1, 1, 1, 0)  # dx, dy, dz, rx, ry, rz

        com_node_tags[floor_num] = com_node

        # Create columns & beams
        create_columns(floor_num, ssmf_cols_node_tags, col_prop, beam_prop)
        create_beams(floor_num, elev, com_node, ssmf_cols_node_tags, ssmf_cols_coord_df, beam_prop, col_prop[0])

    if not_for_optimization:
        print('Floor ' + floor_num + ' created')


# ============================================================================
# Model builder
# ============================================================================
def build_model(beam_Ix_params, not_for_optimization=None):

    # Initialize array of possible values for beam Ix
    bm_mom_inertia_strong = np.array(list(nzs_beams['Ix']))

    # The geometric properties of the beams will be defined relative to the stiffness of the first floor beam
    base_Ix = beam_Ix_params[0] # No need to multiply by 'mm' or '1E6' 417.7432978338827, 0.021177254839192305
    slope_Ix_line = beam_Ix_params[1]

    col_group_heights = np.array([0, 6.2, 15.5, 24.8, 31])  # Height of column groups from the 1st floor

    # Assume linear relationship
    # Base Ix & slope
    bm_Ix_modif = 1 - slope_Ix_line*col_group_heights

    bm_sect_flr_1 = nzs_beams.loc[nzs_beams.index[nzs_beams['Ix'] >= bm_Ix_modif[0] * base_Ix].tolist()[-1]]
    bm_sect_flr_2_to_4 = nzs_beams.loc[nzs_beams.index[nzs_beams['Ix'] >= bm_Ix_modif[1] * base_Ix].tolist()[-1]]
    bm_sect_flr_5_to_7 = nzs_beams.loc[nzs_beams.index[nzs_beams['Ix'] >= bm_Ix_modif[2] * base_Ix].tolist()[-1]]
    bm_sect_flr_8_to_10 = nzs_beams.loc[nzs_beams.index[nzs_beams['Ix'] >= bm_Ix_modif[3] * base_Ix].tolist()[-1]]
    bm_sect_flr_11 = nzs_beams.loc[nzs_beams.index[nzs_beams['Ix'] >= bm_Ix_modif[4] * base_Ix].tolist()[-1]]

    bm_sections = [bm_sect_flr_1.name, bm_sect_flr_2_to_4.name, bm_sect_flr_5_to_7.name, bm_sect_flr_8_to_10.name, bm_sect_flr_11.name]

    bm_prop_flr_1 = [bm_sect_flr_1, bm_E, bm_G, bm_transf_tag_x, bm_transf_tag_y, pzone_transf_tag_bm_x, pzone_transf_tag_bm_y]
    bm_prop_flr_2_to_4 = [bm_sect_flr_2_to_4, bm_E, bm_G, bm_transf_tag_x, bm_transf_tag_y, pzone_transf_tag_bm_x, pzone_transf_tag_bm_y]
    bm_prop_flr_5_to_7 = [bm_sect_flr_5_to_7, bm_E, bm_G, bm_transf_tag_x, bm_transf_tag_y, pzone_transf_tag_bm_x, pzone_transf_tag_bm_y]
    bm_prop_flr_8_to_10 = [bm_sect_flr_8_to_10, bm_E, bm_G, bm_transf_tag_x, bm_transf_tag_y, pzone_transf_tag_bm_x, pzone_transf_tag_bm_y]
    bm_prop_flr_11 = [bm_sect_flr_11, bm_E, bm_G, bm_transf_tag_x, bm_transf_tag_y, pzone_transf_tag_bm_x, pzone_transf_tag_bm_y]

    col_sect_flr_1 = nzs_cols.loc[nzs_cols.index[nzs_cols['Zx'] >= col_beam_mom_ratio * bm_sect_flr_1['Zx']].tolist()[-1]]

    # Keep the same column designation up the building height, while changing to lighter sections
    col_designation = col_sect_flr_1.name

    desig = ''
    for char in col_designation:
        if char == 'B' or char == 'C':
            break
        else:
            desig += char


    col_sect_flr_2_to_4 = nzs_cols.loc[nzs_cols.index[nzs_cols['Zx'] >= col_beam_mom_ratio * bm_sect_flr_2_to_4['Zx']].tolist()[-1]]
    col_sect_flr_5_to_7 = nzs_cols.loc[nzs_cols.index[nzs_cols['Zx'] >= col_beam_mom_ratio * bm_sect_flr_5_to_7['Zx']].tolist()[-1]]
    col_sect_flr_8_to_10 = nzs_cols.loc[nzs_cols.index[nzs_cols['Zx'] >= col_beam_mom_ratio * bm_sect_flr_8_to_10['Zx']].tolist()[-1]]
    col_sect_flr_11 = nzs_cols.loc[nzs_cols.index[nzs_cols['Zx'] >= col_beam_mom_ratio * bm_sect_flr_11['Zx']].tolist()[-1]]

    col_sections = [col_sect_flr_1.name, col_sect_flr_2_to_4.name, col_sect_flr_5_to_7.name, col_sect_flr_8_to_10.name, col_sect_flr_11.name]


    col_prop_flr_1 = [col_sect_flr_1, col_E, col_G, col_transf_tag_EW, col_transf_tag_NS, pzone_transf_tag_col]
    col_prop_flr_2_to_4 = [col_sect_flr_2_to_4, col_E, col_G, col_transf_tag_EW, col_transf_tag_NS, pzone_transf_tag_col]
    col_prop_5_to_7 = [col_sect_flr_5_to_7, col_E, col_G, col_transf_tag_EW, col_transf_tag_NS, pzone_transf_tag_col]
    col_prop_8_to_10 = [col_sect_flr_8_to_10, col_E, col_G, col_transf_tag_EW, col_transf_tag_NS, pzone_transf_tag_col]
    col_prop_flr_11 = [col_sect_flr_11, col_E, col_G, col_transf_tag_EW, col_transf_tag_NS, pzone_transf_tag_col]

    # Model Builder
    ops.wipe()
    ops.model('basic', '-ndm', 3, '-ndf', 6)

    # Create shell material for floor diaphragm
    ops.nDMaterial('ElasticIsotropic', nD_mattag, shell_E, shell_nu)
    ops.nDMaterial('PlateFiber', plate_fiber_tag, nD_mattag)
    ops.section('LayeredShell', shell_sect_tag, 3, plate_fiber_tag, fiber_thick, plate_fiber_tag, fiber_thick, plate_fiber_tag, fiber_thick)

    '''
    # Define geometric transformation for beams
    ops.geomTransf('PDelta', bm_transf_tag_x, 0, -1, 0)
    ops.geomTransf('PDelta', bm_transf_tag_y, 1, 0, 0)  # -1, 0, 0

    # Define geometric transformation for columns
    ops.geomTransf('PDelta', col_transf_tag_EW, 0, 1, 0)
    ops.geomTransf('PDelta', col_transf_tag_NS, 0, 1, 0)
    '''

    # Define geometric transformation for beams
    ops.geomTransf('Linear', bm_transf_tag_x, 0, -1, 0)
    ops.geomTransf('Linear', bm_transf_tag_y, 1, 0, 0)  # -1, 0, 0

    # Define geometric transformation for columns
    ops.geomTransf('Linear', col_transf_tag_EW, 0, 1, 0)
    ops.geomTransf('Linear', col_transf_tag_NS, 0, 1, 0)

    # Define geometric transformation for rigid panel zone elements
    ops.geomTransf('Linear', pzone_transf_tag_col, 0, 1, 0)
    ops.geomTransf('Linear', pzone_transf_tag_bm_x, 0, -1, 0)
    ops.geomTransf('Linear', pzone_transf_tag_bm_y, 1, 0, 0)

    # Create all floors of building
    if not_for_optimization:
        print('Now creating SSMF model... \n')

    create_floor(ground_flr, '00', not_for_optimization)
    create_floor(flr1, '01', not_for_optimization, bm_prop_flr_1, col_prop_flr_1, '1st')
    create_floor(flr2, '02', not_for_optimization, bm_prop_flr_2_to_4, col_prop_flr_2_to_4, '2nd')
    create_floor(flr3, '03', not_for_optimization, bm_prop_flr_2_to_4, col_prop_flr_2_to_4, '3rd')
    create_floor(flr4, '04', not_for_optimization, bm_prop_flr_2_to_4, col_prop_flr_2_to_4, '4th')
    create_floor(flr5, '05', not_for_optimization, bm_prop_flr_5_to_7, col_prop_5_to_7, '5th')
    create_floor(flr6, '06', not_for_optimization, bm_prop_flr_5_to_7, col_prop_5_to_7, '6th')
    create_floor(flr7, '07', not_for_optimization, bm_prop_flr_5_to_7, col_prop_5_to_7, '7th')
    create_floor(flr8, '08', not_for_optimization, bm_prop_flr_8_to_10, col_prop_8_to_10, '8th')
    create_floor(flr9, '09', not_for_optimization, bm_prop_flr_8_to_10, col_prop_8_to_10, '9th')
    create_floor(flr10, '10', not_for_optimization, bm_prop_flr_8_to_10, col_prop_8_to_10, '10th')
    create_floor(roof_flr, '11', not_for_optimization, bm_prop_flr_11, col_prop_flr_11, 'Roof')

    # ============================================================================
    # Create regions for SMF beams & columns based on floor
    # ============================================================================
    if not_for_optimization:

        # Get all element tags
        elem_tags = ops.getEleTags()

        floor_nums = ['01', '02', '03', '04', '05', '06',
                      '07', '08', '09', '10', '11']

        beam_tags = []
        col_tags = []

        for floor in floor_nums:
            floor_bm_tags = []
            floor_col_tags = []

            for tag in elem_tags:

                # Only select beam elements (exclude rigid elements at ends)
                if str(tag).startswith('2' + floor) and len(str(tag)) == 5:
                    floor_bm_tags.append(tag)

                # Only select column elements (exclude rigid elements at ends)
                if str(tag).startswith('3' + floor) and len(str(tag)) == 5:
                    floor_col_tags.append(tag)

            beam_tags.append(floor_bm_tags)
            col_tags.append(floor_col_tags)

        # Beams
        create_beam_region(ops, beam_tags)

        # Columns
        create_column_region(ops, col_tags)

        print('\nBeam sections: ', bm_sections)
        print('\nColumn sections: ', col_sections)

        return bm_sections, col_sections


def run_eigen_gravity_analysis(not_for_optimization=None):

    # Create pvd recorder
    if not_for_optimization:

        record_direc = './pvd/'
        os.makedirs(record_direc, exist_ok=True)
        ops.recorder('PVD', record_direc, '-precision', 3, '-dT', 1, *['mass', 'reaction'], 'eigen', 10)

        # =========================================================================
        # Eigen Analysis
        # =========================================================================
        eigen_report_folder = './'
        angular_freq, periods, modal_prop = run_eigen_analysis(ops, num_modes, damping_ratio, 'SSMF', not_for_optimization, eigen_report_folder)

    else:
        angular_freq, periods = run_eigen_analysis(ops, num_modes, damping_ratio, 'SSMF', not_for_optimization)

    # =========================================================================
    # Gravity analysis
    # =========================================================================
    # Create recorder
    grav_direc = './gravity_results/'
    os.makedirs(grav_direc, exist_ok=True)

    if not_for_optimization:
        ops.recorder('Node', '-file', grav_direc + 'nodeRxn.txt', '-node', *ssmf_cols_node_tags['00'].tolist(), '-dof', 1, 2, 3, 4, 5, 6, 'reaction')
        ops.recorder('Element', '-file', grav_direc + 'col10_forces.txt', '-ele', 20110, 'force')  # Column 10

    num_step_sWgt = 1     # Set weight increments

    ops.constraints('Penalty', 1.0e17, 1.0e17)
    ops.test('NormDispIncr', 1e-6, 100, 0)
    ops.algorithm('KrylovNewton')
    ops.numberer('RCM')
    ops.system('ProfileSPD')
    ops.integrator('LoadControl', 1, 1, 1, 1)
    ops.analysis('Static')

    ops.analyze(num_step_sWgt)

    # Shut down gravity recorders
    ops.remove('recorders')

    if not_for_optimization:
        return angular_freq, periods, modal_prop

    else:
        return angular_freq, periods


# ELF analysis
def run_elf_analysis(periods, pattern_type, not_for_optimization=None):

    # Extract eigen vector values for the COM node
    com_nodes_eigen = list(com_node_tags.values())

    com_eigen_vec_x = np.zeros(len(com_node_tags))
    com_eigen_vec_y = np.zeros(len(com_node_tags))


    for ii in range(len(com_nodes_eigen)):
        com_eigen_vec_x[ii] = ops.nodeEigenvector(com_nodes_eigen[ii], 1, 1)
        com_eigen_vec_y[ii] = ops.nodeEigenvector(com_nodes_eigen[ii], 1, 2)

    # Normalize mode shapes by the mode shape of the topmost floor
    com_eigen_vec_x /=  com_eigen_vec_x[-1]
    com_eigen_vec_y /=  com_eigen_vec_y[-1]

    spectral_shape_factor = spectral_shape_fac(periods[0])
    hazard_factor = 0.13
    return_per_factor_sls = 0.25
    return_per_factor_uls = 1.3
    fault_factor = 1.0
    perform_factor = 0.7
    story_masses = np.array(list(total_floor_mass.values()))
    story_weights = story_masses * grav_metric
    seismic_weight = story_weights.sum()

    elf_base_shear = nz_horiz_seismic_shear(spectral_shape_factor, hazard_factor,
                                            return_per_factor_sls, return_per_factor_uls,
                                            fault_factor, perform_factor, ductility_factor,
                                            seismic_weight)

    if pattern_type == 'modal':
        # Distribute story forces used Mode 1 eigen shape
        push_pattern = (
                        elf_base_shear * (com_eigen_vec_x * story_masses) /
                        (np.sum(com_eigen_vec_x * story_masses))
                        )  # EC8-Part 1 Eqn. 4.10

    else:  # pattern_type == 'triangular':
        push_pattern = nz_horiz_force_distribution(elf_base_shear, story_weights,
                                                        np.cumsum(story_heights))

    'Maintain constant gravity loads and reset time to zero'
    ops.loadConst('-time', 0.0)
    ops.wipeAnalysis()

    # Assign lateral loads
    ts_tag = 11000
    pattern_tag = 11000

    ops.timeSeries('Constant', ts_tag)
    ops.pattern('Plain', pattern_tag, ts_tag)

    for jj in range(len(story_heights)):
        ops.load(com_nodes_eigen[jj], push_pattern[jj], 0., 0., 0., 0., 0.)

    if not_for_optimization:
        # Create directory to save results
        elf_res_folder = './ELF_results/'
        os.makedirs(elf_res_folder, exist_ok=True)

        # Create recorders
        ops.recorder('Element', '-file', elf_res_folder + 'floor01_beamResp.txt',
                      '-precision', 9, '-region', 201, 'force')

        ops.recorder('Element', '-file', elf_res_folder + 'floor01_colResp.txt',
                      '-precision', 9, '-region', 301, 'force')

        ops.recorder('Node', '-file', elf_res_folder + 'baseShear.txt', '-node',
                      *ssmf_cols_node_tags['00'].tolist(), '-dof', 1, 'reaction')  # Fx

        # The nodal rxns here should match the axial loads obtained from the
        # column elements above
        ops.recorder('Node', '-file', elf_res_folder + 'baseRxn.txt', '-node',
                      *ssmf_cols_node_tags['00'].tolist(), '-dof', 3, 'reaction')  # Fz

    # Perform ELF analysis
    num_step_sWgt = 1     # Set weight increments

    ops.constraints('Penalty', 1.0e17, 1.0e17)
    ops.test('NormDispIncr', 1e-6, 100, 0)
    ops.algorithm('KrylovNewton')
    ops.numberer('RCM')
    ops.system('ProfileSPD')
    ops.integrator('LoadControl', 1, 1, 1, 1)
    ops.analysis('Static')

    ops.analyze(num_step_sWgt)

    if not_for_optimization:

        print('=============================================================')
        print('\nELF analysis completed...')

        # Shut down recorders
        ops.remove('recorders')

        # Load ELF results
        # elf_beam_demands = np.loadtxt(elf_res_folder + 'floor01_beamResp.txt')
        elf_col_demands = np.loadtxt(elf_res_folder + 'floor01_colResp.txt')
        # elf_nodal_rxn_Fz = np.loadtxt(elf_res_folder + 'baseRxn.txt')

        # Process nodal rxns.
        # elf_nodal_rxn_combined = pd.DataFrame(get_mvlem_base_rxn(elf_nodal_rxn_Fz), columns=['Fz (kN)'],
        #                                  index=list(wall_prop_df.index) + list(col_coords_df.index))

        # Process ELF demands
        '''
        There are 23 columns on each floor with each column defined by
        2 nodes (i & j).

        At each node, there are 6-DOFs, hence each column has 12-DOFs.
        [Fxi, Fyi, Fzi, Mxi, Myi, Mzi, Fxj, Fyj, Fzj, Mxj, Myj, Mzj ]

        Total column DOFs per floor = 23 * 12 = 276.

        The element forces at the top node (j) of each column will be equal in
        in magnitude to that at its base (i). Hence, we only extract the forces
        at the i-node for each column.
        '''
        elf_col_Fx = elf_col_demands[0::12]
        elf_col_Fy = elf_col_demands[1::12]
        elf_col_Fz = elf_col_demands[2::12]

        elf_col_demands_df = pd.DataFrame({'Fx-kN': elf_col_Fx,
                                           'Fy-kN': elf_col_Fy,
                                           'Fz-kN': elf_col_Fz}, index=ssmf_cols_coord_df.index)

        return story_weights, push_pattern,  elf_base_shear, elf_col_demands_df

    else:
        return story_weights, push_pattern,  elf_base_shear


def run_mrsa(angular_freq, elf_base_shear, not_for_optimization=None):

    # Load spectral accelerations and periods for response spectrum
    spect_acc = np.loadtxt('../nz_spectral_acc.txt') / ductility_factor
    spect_periods = np.loadtxt('../nz_periods.txt')

    perform_mrsa(ops, spect_acc, spect_periods, num_modes, './mrsa_results/dir',
                 ssmf_cols_node_tags, not_for_optimization, com_node_tags=com_node_tags, lfrs='ssmf')

    if not_for_optimization:
        print('\nMRSA completed.')
        print('======================================================')

    # ============================================================================
    # Post-process MRSA results
    # ============================================================================
    mrsa_base_shearX = modal_combo(np.loadtxt('./mrsa_results/dirX/baseShearX.txt'),
                                   angular_freq, damping_ratio, num_modes).sum()

    mrsa_base_shearY = modal_combo(np.loadtxt('./mrsa_results/dirY/baseShearY.txt'),
                                   angular_freq, damping_ratio, num_modes).sum()

    # Compute factors for scaling MRSA demands to ELF demands NZS 1170.5:2004 - Sect. 5.2.2.2b
    elf_mrsaX_scale_factor = max(elf_base_shear / mrsa_base_shearX, 1.0)
    elf_mrsaY_scale_factor = max(elf_base_shear / mrsa_base_shearY, 1.0)

    # Load in COM displacements from MRSA
    mrsa_com_dispX = np.loadtxt('./mrsa_results/dirX/COM_dispX.txt')  # For MRSA in x-direction
    mrsa_com_dispY = np.loadtxt('./mrsa_results/dirY/COM_dispY.txt')  # For MRSA in y-direction

    return mrsa_com_dispX, mrsa_com_dispY, elf_mrsaX_scale_factor, elf_mrsaY_scale_factor


def run_pdelta_analysis(beam_Ix_params, pdelta_method, angular_freq, periods, story_weights,
                        mrsa_com_dispX, mrsa_com_dispY, elf_base_shear, push_pattern,
                            elf_mrsaX_fac, elf_mrsaY_fac, results_root_folder=None,
                            not_for_optimization=None):

    if pdelta_method == 'A':

        # Compute story drifts
        story_driftX = compute_story_drifts(mrsa_com_dispX, story_heights, angular_freq, damping_ratio, num_modes)
        story_driftY = compute_story_drifts(mrsa_com_dispY, story_heights, angular_freq, damping_ratio, num_modes)

        # Scale drifts by elf-to-mrsa base shear factor # NZS 1170.5-2004: Sect 5.2.2.2b
        story_driftX *= elf_mrsaX_fac
        story_driftY *= elf_mrsaY_fac

        kp  = 0.015 + 0.0075*(ductility_factor - 1)
        kp = min(max(0.0015, kp), 0.03)
        pdelta_fac = (kp * story_weights.sum() + elf_base_shear) / elf_base_shear  # NZS 1170.5-2004: Sec 7.2.1.2 & 6.5.4.1

        # Amplify drifts by required factors
        story_driftX *=  (ductility_factor * pdelta_fac * drift_modif_fac)
        story_driftY *=  (ductility_factor * pdelta_fac * drift_modif_fac)


    else:  # pdelta_method == 'B' (NZS 1170.5:2004 - Sect. 6.5.4.2 & Commentary Sect. C6.5.4.2)

        # Modal combination on peak COM displacements from MRSA
        mrsa_total_com_dispX = modal_combo(mrsa_com_dispX, angular_freq, damping_ratio, num_modes)
        mrsa_total_com_dispY = modal_combo(mrsa_com_dispY, angular_freq, damping_ratio, num_modes)

        # Scale COM displacements by elf-to-mrsa base shear factor # NZS 1170.5-2004: Sect 5.2.2.2b
        mrsa_total_com_dispX *= elf_mrsaX_fac
        mrsa_total_com_dispY *= elf_mrsaY_fac

        # Amplify COM displacements by ductility factor
        # NZS 1170.5:2004 Commentary Sect. C6.5.4.2 Step 2
        mrsa_total_com_dispX *= ductility_factor
        mrsa_total_com_dispY *= ductility_factor

        # Compute interstory displacements
        inter_story_dispX = np.insert(np.diff(mrsa_total_com_dispX), 0, mrsa_total_com_dispX[0])
        inter_story_dispY = np.insert(np.diff(mrsa_total_com_dispY), 0, mrsa_total_com_dispY[0])

        # Compute story shear force due to PDelta actions
        # NZS 1170.5:2004 Commentary Sect. C6.5.4.2 Step 3a
        story_shear_forceX  = story_weights * inter_story_dispX / story_heights
        story_shear_forceY  = story_weights * inter_story_dispY / story_heights

        # Compute lateral forces to be used in static analysis for PDelta effects
        # NZS 1170.5:2004 Commentary Sect. C6.5.4.2 Step 3b
        lateral_forces_pDeltaX = np.insert(np.diff(story_shear_forceX), 0, story_shear_forceX[0])
        lateral_forces_pDeltaY = np.insert(np.diff(story_shear_forceY), 0, story_shear_forceY[0])


    # ===================================================================================================
    # Perform static analysis for accidental torsional moment (PDelta method A & B)
    # & for PDelta effects (PDelta method B)
    # ===================================================================================================
    floor_dimen_x = 29.410 * m
    floor_dimen_y = 31.025 * m

    accid_ecc_x = floor_dimen_x / 10
    accid_ecc_y = floor_dimen_y / 10

    torsional_mom_x = push_pattern * accid_ecc_y
    torsional_mom_y = push_pattern * accid_ecc_x

    # AMPLIFY TORSIONAL MOMENT IF REQUIRED BY CODE
    # New Zealand does not require amplification of accidental torsional moment

    torsional_direc = ['X', 'Y']
    elf_dof = [1, 2]
    torsional_sign = [1, -1]
    torsional_folder = ['positive', 'negative']

    # Perform static analysis for loading in X & Y direction
    for ii in range(len(torsional_direc)):

        # For each direction, account for positive & negative loading
        for jj in range(len(torsional_sign)):

            if not_for_optimization:
                print('\nNow commencing static analysis using torsional moments for '
                      + torsional_folder[jj] + ' ' + torsional_direc[ii] + ' direction.')

            build_model(beam_Ix_params, not_for_optimization)

            # if not_for_optimization:
            #     print('\nModel generated...')

            # Impose torsional moments at COMs
            com_nodes = list(com_node_tags.values())

            # Assign torsional moments
            ts_tag = 20000
            pattern_tag = 20000

            ops.timeSeries('Constant', ts_tag)
            ops.pattern('Plain', pattern_tag, ts_tag)

            # Loop through each COM node and apply torsional moment & PDelta lateral force if applicable
            for kk in range(len(com_nodes)):

                if torsional_direc[ii] == 'X' and pdelta_method == "A":  # Only torsional moment is applied about z-axis
                    ops.load(com_nodes[kk], 0., 0., 0., 0., 0., torsional_mom_x[kk] * torsional_sign[jj])

                elif torsional_direc[ii] == 'X' and pdelta_method == "B": # Torsional moment about z-axis & PDelta "Method B" forces are applied
                    ops.load(com_nodes[kk], lateral_forces_pDeltaX[kk], 0., 0., 0., 0., torsional_mom_x[kk] * torsional_sign[jj])

                elif torsional_direc[ii] == 'Y' and pdelta_method == "A":  # Only torsional moment is applied about z-axis
                    ops.load(com_nodes[kk], 0., 0., 0., 0., 0., torsional_mom_y[kk] * torsional_sign[jj])

                elif torsional_direc[ii] == 'Y' and pdelta_method == "B":  # Torsional moment about z-axis & PDelta "Method B" forces are applied
                    ops.load(com_nodes[kk], 0., lateral_forces_pDeltaY[kk], 0., 0., 0., torsional_mom_y[kk] * torsional_sign[jj])

            # Create directory to save results
            accident_torsion_res_folder = results_root_folder + '/accidental_torsion_results/' + torsional_folder[jj] + torsional_direc[ii] + '/'
            os.makedirs(accident_torsion_res_folder, exist_ok=True)

            if not_for_optimization:
                # Create recorder for beam-response in direction of static loading
                create_beam_recorders(ops, accident_torsion_res_folder)

                # Create recorders for column response direction of static loading
                create_column_recorders(ops, accident_torsion_res_folder)

            # Recorders for COM displacement
            ops.recorder('Node', '-file', accident_torsion_res_folder + 'COM_disp' + torsional_direc[ii] + '.txt',
                         '-node', *list(com_node_tags.values()), '-dof', elf_dof[ii], 'disp')

            # Base shear
            ops.recorder('Node', '-file', accident_torsion_res_folder + 'baseShear' + torsional_direc[ii] + '.txt', '-node',
                          *ssmf_cols_node_tags['00'].tolist(), '-dof', elf_dof[ii], 'reaction')  # Fx or Fy

            # Perform static analysis
            num_step_sWgt = 1     # Set weight increments

            ops.constraints('Penalty', 1.0e17, 1.0e17)
            ops.test('NormDispIncr', 1e-6, 100, 0)
            ops.algorithm('KrylovNewton')
            ops.numberer('RCM')
            ops.system('ProfileSPD')
            ops.integrator('LoadControl', 1, 1, 1, 1)
            ops.analysis('Static')

            ops.analyze(num_step_sWgt)

            # Shut down recorders
            ops.remove('recorders')

            # Clear model
            ops.wipe()

            # print('=============================================================')

    print('\nStatic analysis for accidental torsion completed...')


    if pdelta_method == "B":

        # Process drifts due to PDelta lateral forces
        pdelta_com_disp_posX = np.loadtxt(results_root_folder + '/accidental_torsion_results/positiveX/COM_dispX.txt')
        pdelta_com_disp_negX = np.loadtxt(results_root_folder + '/accidental_torsion_results/negativeX/COM_dispX.txt')
        pdelta_com_disp_posY = np.loadtxt(results_root_folder + '/accidental_torsion_results/positiveY/COM_dispY.txt')
        pdelta_com_disp_negY = np.loadtxt(results_root_folder + '/accidental_torsion_results/negativeY/COM_dispY.txt')

        pdelta_com_dispX = np.maximum(pdelta_com_disp_posX, pdelta_com_disp_negX)
        pdelta_com_dispY = np.maximum(pdelta_com_disp_posY, pdelta_com_disp_negY)

        # Determine subsoil factor NZS 1170.5:2004 Sect. C6.5.4.2 Step 4
        # Case study building is in site subclass C.
        if periods[0] < 2.0:
            subsoil_factor_K = 1.0
        elif 2.0 <= periods[0] <= 4.0:
            subsoil_factor_K = (6 - periods[0]) / 4
        else:
            subsoil_factor_K = 4


        if ductility_factor <= 3.5:
            subsoil_factor_beta = 2 * ductility_factor * subsoil_factor_K / 3.5
        else:
            subsoil_factor_beta = 2 * subsoil_factor_K

        subsoil_factor_beta = max(subsoil_factor_beta, 1.0)

        # When using method B, element demands need to be scaled up by subsoil_factor_beta
        pdelta_fac = subsoil_factor_beta

        # Amplify PDelta COM displacements by subsoil_factor_beta and ductility factor
        pdelta_com_dispX *= (subsoil_factor_beta * ductility_factor)
        pdelta_com_dispY *= (subsoil_factor_beta * ductility_factor)

        # Add up COM displacements fropm MRSA & PDelta checks
        total_com_dispX = mrsa_total_com_dispX + pdelta_com_dispX
        total_com_dispY = mrsa_total_com_dispY + pdelta_com_dispY

        # Compute total interstory displacements
        total_inter_story_dispX = np.insert(np.diff(total_com_dispX), 0, total_com_dispX[0])
        total_inter_story_dispY = np.insert(np.diff(total_com_dispY), 0, total_com_dispY[0])

        # Compute story drift ratios
        story_driftX  = total_inter_story_dispX / story_heights * 100
        story_driftY  = total_inter_story_dispY / story_heights * 100

        # Amplify story drift ration by drift factor
        story_driftX *= drift_modif_fac
        story_driftY *= drift_modif_fac

    max_story_drift = max(story_driftX.max(), story_driftY.max())

    # CHECK STABILITY REQUIREMENTS (P-DELTA) NZS 1170.5:2004 - Sect 6.5.1
    thetaX = story_weights * 0.01 * story_driftX / (push_pattern * story_heights)
    thetaY = story_weights * 0.01 * story_driftY / (push_pattern * story_heights)

    max_theta = max(thetaX.max(), thetaY.max())

    # Save story drifts
    if not_for_optimization:

        np.savetxt('driftX-PDeltaMethod{}.txt'.format(pdelta_method), story_driftX, fmt='%.2f')
        np.savetxt('driftY-PDeltaMethod{}.txt'.format(pdelta_method), story_driftY, fmt='%.2f')

        # CHECK DRIFT REQUIREMENTS
        drift_ok = max_story_drift < 2.5  # Maximum story drift limit = 2.5%  NZS 1170.5:2004 - Sect 7.5.1

        print('\nMaximum story drift: {:.3f}%'.format(max_story_drift))
        if drift_ok:
            print('Story drift requirements satisfied.')
        else:
            print('Story drift requirements NOT satisfied.')


        theta_ok = max_theta < 0.3

        print('\nMaximum stability coefficient: {:.3f}'.format(max_theta))
        if theta_ok:
            print('Stability requirements satisfied.')
        else:
            print('Stability requirements NOT satisfied.')

        return story_driftX, story_driftY, pdelta_fac

    else:
        return max_story_drift, max_theta


def get_mrsa_and_torsional_demands(angular_freq, pdelta_fac, elf_mrsaX_fac,
                                           elf_mrsaY_fac, mrsa_folder, acc_torsion_folder):

    # ========================================================================
    # Post-process MRSA & accidental torsion results
    # ========================================================================
    beam_demands_X = process_beam_col_resp('beam', mrsa_folder + '/dirX/', acc_torsion_folder + '/positiveX/',
                                          acc_torsion_folder + '/negativeX/', angular_freq, damping_ratio,
                                          num_modes, elf_mrsaX_fac, pdelta_fac)

    beam_demands_Y = process_beam_col_resp('beam', mrsa_folder + '/dirY/', acc_torsion_folder + '/positiveY/',
                                          acc_torsion_folder + '/negativeY/', angular_freq, damping_ratio,
                                          num_modes, elf_mrsaY_fac, pdelta_fac)

    col_demands_X = process_beam_col_resp('col', mrsa_folder + '/dirX/', acc_torsion_folder + '/positiveX/',
                                          acc_torsion_folder + '/negativeX/', angular_freq, damping_ratio,
                                          num_modes, elf_mrsaX_fac, pdelta_fac)

    col_demands_Y = process_beam_col_resp('col', mrsa_folder + '/dirY/', acc_torsion_folder + '/positiveY/',
                                          acc_torsion_folder + '/negativeY/', angular_freq, damping_ratio, num_modes,
                                          elf_mrsaY_fac, pdelta_fac)

    return beam_demands_X, beam_demands_Y, col_demands_X, col_demands_Y


def generate_story_drift_plots(pdelta_method, story_driftX, story_driftY):

    # Generate story drift plots
    fig, ax = plt.subplots(1, 2, figsize=(6.0, 7.5), sharex=True, sharey=True, constrained_layout=True)
    fig.suptitle('Story drift ratios - PDelta Method {}'.format(pdelta_method), fontdict=title_font)

    ax[0].vlines(story_driftX[0], 0.0, elev[0])
    ax[1].vlines(story_driftY[0], 0.0, elev[0])

    for ii in range(1, len(story_driftX)):
        ax[0].hlines(elev[ii-1], story_driftX[ii-1], story_driftX[ii])
        ax[0].vlines(story_driftX[ii],  elev[ii-1], elev[ii])

        ax[1].hlines(elev[ii-1], story_driftY[ii-1], story_driftY[ii])  # Correct
        ax[1].vlines(story_driftY[ii],  elev[ii-1], elev[ii])


    ax[0].set_title('X - Direction', fontsize=12, family='Times New Roman')
    ax[1].set_title('Y- Direction', fontsize=12, family='Times New Roman')

    ax[0].set_ylabel('Story elevation (m)', fontdict=axes_font)

    for axx in ax.flat:
        axx.set_xlim(0.0)
        axx.set_ylim(0.0, elev[-1])

        axx.grid(True, which='major', axis='both', ls='-.', linewidth=0.6)

        axx.set_yticks(elev)

        axx.set_xlabel('Story drift ratio (%)', fontdict=axes_font)

        axx.yaxis.set_major_formatter(StrMethodFormatter('{x:,.1f}'))
        axx.tick_params(axis='both', direction='in', colors='grey', labelcolor='grey', zorder=3.0, labelsize=8.0)

    # plt.savefig('DriftPlots-PDeltaMethod{}.png'.format(pdelta_method), dpi=1200)


def check_beam_strength(bm_sections, beam_demands_X, beam_demands_Y):

    # CHECK STRENGTH REQUIREMENTS
    # Create array of design flexural strengths for beam sections per floor
    bm_nominal_strengths = 0.9 * steel_Fy * np.array([
                                                    nzs_beams.loc[bm_sections[0]]['Zx'],
                                                    nzs_beams.loc[bm_sections[1]]['Zx'],
                                                    nzs_beams.loc[bm_sections[1]]['Zx'],
                                                    nzs_beams.loc[bm_sections[1]]['Zx'],
                                                    nzs_beams.loc[bm_sections[2]]['Zx'],
                                                    nzs_beams.loc[bm_sections[2]]['Zx'],
                                                    nzs_beams.loc[bm_sections[2]]['Zx'],
                                                    nzs_beams.loc[bm_sections[3]]['Zx'],
                                                    nzs_beams.loc[bm_sections[3]]['Zx'],
                                                    nzs_beams.loc[bm_sections[3]]['Zx'],
                                                    nzs_beams.loc[bm_sections[4]]['Zx']]) * 1E3 * mm**3  # result in kN-m

    # Initialize DataFrame to save flexural demand & design strengths.
    bm_flexural_design = pd.DataFrame(columns=['Floor', 'Phi-Mn (kN-m)', 'Mu (kN-m)', 'Satisfactory'], index=beam_demands_X.index)
    bm_flexural_design['Floor'] = beam_demands_X['Floor']
    bm_flexural_design['Phi-Mn (kN-m)'] = bm_nominal_strengths
    bm_flexural_design['Mu (kN-m)'] = pd.concat([
                                                beam_demands_X[['Mx (kN-m)','My (kN-m)']],
                                                beam_demands_Y[['Mx (kN-m)','My (kN-m)']]], axis=1).max(axis=1)

    bm_flexural_design['Satisfactory'] = bm_flexural_design['Phi-Mn (kN-m)'] >= bm_flexural_design['Mu (kN-m)']

    # Verify that the design flexural strength of beams on all floors >= flexural demand
    bm_flexural_satisfied = (bm_flexural_design['Satisfactory'] == True).all()

    if bm_flexural_satisfied:
        print('\nBeam flexural requirements are satisfied!.')
    else:
        print('\nBeam flexural requirements are NOT satisfied!.')


def check_column_strength():
    pass
