#include <stdio.h>
#include <windows.h>
#include <conio.h>

#define BLE_COMMAND "py -3.13 -u ble_receiver.py"
#define MAX_MEASUREMENTS 10U
#define ROWS_PER_MEASUREMENT 103U

int main(void)
{
    char line[256];
    const char filename[] = "1ballnickssoftball.csv";

    unsigned int impact_number;
    unsigned int time_ms;
    unsigned int first_time_ms = 0U;
    unsigned int last_impact_number = 0U;
    unsigned int row_count = 0U;
    unsigned int impact_count = 0U;
    unsigned int rows_in_current_measurement = 0U;

    int ax_mg;
    int ay_mg;
    int az_mg;
    int total_mg;

    FILE *file = fopen(filename, "w");

    if (file == NULL)
    {
        printf("Could not create data file.\n");
        return 1;
    }

    printf("Starting Bluetooth receiver...\n");

    FILE *ble = _popen(BLE_COMMAND, "r");

    if (ble == NULL)
    {
        printf("Could not start Bluetooth receiver.\n");
        fclose(file);
        return 1;
    }

    printf(
        "Waiting for saved impacts (maximum %u complete measurements).\n",
        MAX_MEASUREMENTS
    );
    printf("Press Q to stop.\n\n");

    while (1)
    {
        if (kbhit())
        {
            char key = getch();

            if (key == 'q' || key == 'Q')
            {
                break;
            }
        }

        if (fgets(line, sizeof(line), ble) == NULL)
        {
            break;
        }

        int values = sscanf(
            line,
            "%u,%u,%d,%d,%d,%d",
            &impact_number,
            &time_ms,
            &ax_mg,
            &ay_mg,
            &az_mg,
            &total_mg
        );

        if (values == 6)
        {
            if (impact_number != last_impact_number)
            {
                last_impact_number = impact_number;
                rows_in_current_measurement = 0U;
                printf("Receiving impact %u...\n", impact_number);
            }

            double time_seconds =
                (time_ms) / 1000.0;

            fprintf(
                file,
                "%u,%.3f,%.3f,%.3f,%.3f,%.3f\n",
                impact_number,
                time_seconds,
                ax_mg / 1000.0,
                ay_mg / 1000.0,
                az_mg / 1000.0,
                total_mg / 1000.0
            );

            row_count++;
            rows_in_current_measurement++;

            if (rows_in_current_measurement >= ROWS_PER_MEASUREMENT)
            {
                impact_count++;

                printf(
                    "Measurement %u/%u complete.\n",
                    impact_count,
                    MAX_MEASUREMENTS
                );

                if (impact_count >= MAX_MEASUREMENTS)
                {
                    break;
                }
            }
        }
    }

    fflush(file);
    fclose(file);
    _pclose(ble);

    printf(
        "\nReceived %u impacts and %u measurement rows.\n",
        impact_count,
        row_count
    );
    printf("Saved as: %s\n", filename);

    if (row_count == 0U)
    {
        return 0;
    }

    FILE *gnuplot = _popen("gnuplot -persistent", "w");

    if (gnuplot == NULL)
    {
        printf("Could not start GNUplot.\n");
        return 1;
    }

    fprintf(gnuplot, "set datafile separator ','\n");
    fprintf(gnuplot, "set title 'Saved impact acceleration'\n");
    fprintf(gnuplot, "set xlabel 'Time (seconds)'\n");
    fprintf(gnuplot, "set ylabel 'Acceleration (g)'\n");
    fprintf(gnuplot, "set grid\n");
    fprintf(gnuplot, "set key top right\n");

    fprintf(
        gnuplot,
        "plot "
        "'%s' using 2:3 with lines lw 2 lc rgb 'red' title 'X', "
        "'%s' using 2:4 with lines lw 2 lc rgb 'green' title 'Y', "
        "'%s' using 2:5 with lines lw 2 lc rgb 'blue' title 'Z', "
        "'%s' using 2:6 with lines lw 2 lc rgb 'purple' title 'Total'\n",
        filename,
        filename,
        filename,
        filename
    );

    fflush(gnuplot);
    _pclose(gnuplot);

    return 0;
}
