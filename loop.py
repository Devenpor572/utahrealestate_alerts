import manager
import shared


def loop_sleep():
    shared.sleep_norm_dist(900, 120, 300)


if __name__ == '__main__':
    while True:
        manager.update()
        loop_sleep()
