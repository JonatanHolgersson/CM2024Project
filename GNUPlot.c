#include <stdio.h>
#include <time.h>

#define COMMAND_LENGTH 255

typedef struct PlotSettings
{
    char fileName[COMMAND_LENGTH];
    char title[COMMAND_LENGTH];
    char style[COMMAND_LENGTH];
} PlotSet;

typedef struct GnuSettings
{
    char title[COMMAND_LENGTH];
    char xLabel[COMMAND_LENGTH];
    char yLabel[COMMAND_LENGTH];
    PlotSet plot;
} GnuSet;



int main(void) {
    GnuSet plotSettings = {
        .title = "set title \"Serious Head Injuries\"",
        .xLabel = "set xlabel \"Time\"",
        .yLabel = "set ylabel \"Force\"",
        .plot = {
            .fileName = "measurements.txt",
            .title = "This is our graph",
            .style = "with lines"
        }
    };

    FILE *gnupipe = NULL;
    gnupipe = _popen("gnuplot -persistent", "w");

    //Execute gnucommands
    fprintf(gnupipe, "%s\n", plotSettings.title);
    fprintf(gnupipe, "%s\n", plotSettings.xLabel);
    fprintf(gnupipe, "%s\n", plotSettings.yLabel);
    fprintf(gnupipe, "plot '%s' %s title '%s'\n", plotSettings.plot.fileName, plotSettings.plot.style, plotSettings.plot.title);

    return 0;
}
