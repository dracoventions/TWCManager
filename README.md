# TWCManager
TWCManager lets you control the amount of power delivered by a Tesla Wall Connector (TWC) to the car it's charging.

**TWCs released after around December 2017 can not currently be controlled by TWCManager.**  I have not yet found a way to stop newer TWCs from charging without risking putting the car into an error state where it will not charge again until the TWC is re-plugged.  I will release new code if I can find a solution.  I wrote a workaround that uses the same API as the phone app which you can learn about [here](https://teslamotorsclub.com/tmc/posts/2725885/).  I am still exploring other methods before I decide if that is the best solution and update github.

Due to hardware limitations, TWCManager will not work with Tesla's older High Power Wall Connector (HPWC) EVSEs that were discontinued around April 2016.

See **TWCManager Installation.pdf** for how to install and use.
