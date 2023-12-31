'''
This script uses different notations from the paper, please see below (some of) the correspondance:

    script      |       paper   
----------------+------------------- 
    phi         |       phi_D
    psi         |       phi_I
    r1          |       rho_D
    r2          |       rho_I
    ...         |       ...
----------------+-------------------
'''

import os
import time
import matplotlib.pyplot as plt
import matplotlib.patches

from RK4 import rk4 
from vecgram import *
from math import atan2, pi, sqrt, cos, sin, acos, tan
from Config import Config

sector_angle = Config.SECTOR_ANGLE # sector angle of the defender


'''
the dynamic model of the system after optimal controls are applied.
input: 					   4D state containing 	  	rho_D, 		theta_D, 	  rho_I, 	 theta_I
										s =	   	  ( rho_D, 		theta_D, 	  rho_I, 	 theta_I)
output: time derivative of 4D state containing dot(rho_D), dot(theta_D), dot(rho_I), dot(theta_I)

state (input) --> optimal control (phi, computed by get_phi)
   |		  				|
   -------------------> velocity_vec ----> time derivative of state
'''
def envelope_dx(s):
	"""
    Computes the time derivative of the state vector based on the optimal control strategy.

    Parameters:
    s (array): State vector consisting of [rho_D, theta_D, rho_I, theta_I].

    Returns:
    np.array: Time derivative of the state vector [dot(rho_D), dot(theta_D), dot(rho_I), dot(theta_I)].
    """
	phi = get_phi(s[0], s[2])
	vr1, vr2, vtht1, vtht2 = velocity_vec(s[0], s[2], phi, backward=False)
	# print('dr: [%.5f, %.5f]'%(s[0], s[2]), 'dv: [%.5f, %.5f]'%(vr1, vr2), 'phi: [%.5f]'%(phi))
	return np.array([vr1, vtht1, vr2, vtht2])


# starting from given (r1, r2), integrate envelope_dx() to generate an optimal trajectory
# the envelope barrier of the game is made of such trajectories
def envelope_barrier(r1, r2, tht1=0, dt=0.05):
	"""
    Generates an optimal trajectory forming part of the envelope barrier by integrating the state vector.

    Parameters:
    r1 (float): Initial radial distance of the defender from the target center.
    r2 (float): Initial radial distance of the intruder from the target center.
    tht1 (float): Initial angular position of the defender. Default is 0.
    dt (float): Time step for integration. Default is 0.05 seconds.

    Returns:
    tuple: Contains the trajectory in Cartesian coordinates, the state vector, optimal control angles,
           ratio of radii, and time stamps for the trajectory.
    """

	# to store the computed trajectory, so as to generate Figure 16
	# one call to envelope_barrier( .. ) will compute only one trajectory in Figure 16
	# so we need to specify different (r1, r2) and call envelope_barrier( .. ) several times
	fname = 'res/r1_%.3f-r2_%.3f'%(r1, r2)+'/data.csv'
	if not os.path.isdir('res/r1_%.3f-r2_%.3f'%(r1, r2)+'/'):
		os.makedirs('res/r1_%.3f-r2_%.3f'%(r1, r2)+'/')

	# See equation (19)
	dtht = acos((r1**2 + r2**2 - r**2)/(2*r1*r2))

	# assemble rho_D, theta_D, rho_I, theta_I into a 4D vector, which will be feed to envelope_dx
	ss = [np.array([r1, tht1, r2, tht1-dtht])]
	ts = [0] # initial time, set to 0

	t = 0
	while t < 60:

		# check if capture is possible 
		if abs(ss[-1][0] - ss[-1][2]) >= r - dt*vi or ss[-1][0] + ss[-1][2] <= r + dt*vi:
			print('can\'t cap')
			break
		# print(t)

		# integrate and append to ss
		s_ = rk4(envelope_dx, ss[-1], dt)
		ss.append(s_)
		t += dt
		ts.append(t)

	# to convert from state space (rho_D, theta_D, rho_I, theta_I) to (x_D, y_D, x_I, y_I)
	xs, phis, rrs = [], [], []
	for s in ss:
		# pritn(s)
		xd = s[0]*cos(s[1])
		yd = s[0]*sin(s[1])
		xi = s[2]*cos(s[3])
		yi = s[2]*sin(s[3])
		x = [xd, yd, xi, yi]
		xs.append(x)
		phi = get_phi(s[0], s[2])
		phis.append(phi)
		rrs.append(s[2]/s[0])
		with open(fname, 'a') as f:
			f.write(','.join(list(map(str, s)))+',%.10f\n'%phi)
		# print(sqrt((xd - xi)**2 + (yd - yi)**2))

	return np.asarray(xs), np.asarray(ss), phis, rrs, np.asarray(ts)

def is_within_sector(xd, yd, xi, yi, capture_radius=r, sector_angle=sector_angle):
    """
    Check if the intruder is within the sector-shaped capture range of the defender.

    Args:
    xd (float): x-coordinate of the defender.
    yd (float): y-coordinate of the defender.
    xi (float): x-coordinate of the intruder.
    yi (float): y-coordinate of the intruder.
    capture_radius (float): Radius of the capture sector.
    sector_angle (float): Angle of the sector (in radians).

    Returns:
    bool: True if the intruder is within the capture range, False otherwise.
    """
    distance = sqrt((xi - xd)**2 + (yi - yd)**2)
    angle = atan2(yi - yd, xi - xd) % (2 * pi)
    return distance <= capture_radius and angle <= sector_angle