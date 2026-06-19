#!/bin/bash

NOTES_DIR="$HOME/Documents/Notes"

# Ensure the directory exists
mkdir -p "$NOTES_DIR"

# Fetch all .txt files
IFS=$'\n' files=($(ls "$NOTES_DIR" | grep '\.txt$'))

echo "Choose an option or a note to open:"
PS3="Enter a number: "

# Main Menu
select opt in "Create New Note" "Search Inside Notes" "${files[@]}" "Exit"; do
    case "$opt" in
        "Create New Note")
            read -p "Enter title for new note: " filename
            [[ "$filename" != *.txt ]] && filename="${filename}.txt"
            
            touch "$NOTES_DIR/$filename"
            gnome-text-editor "$NOTES_DIR/$filename" &
            break
            ;;
            
        "Search Inside Notes")
            if [ ${#files[@]} -eq 0 ]; then
                echo "No notes available to search."
                echo ""
                continue
            fi

            # Continuous search loop
            while true; do
                read -p "Enter search term (or press Enter to go back): " query
                
                # If input is blank, exit the search loop and return to main menu
                if [ -z "$query" ]; then
                    echo "Returning to main menu."
                    echo ""
                    break
                fi
                
                # Find filenames that contain the match
                IFS=$'\n' match_files=($(grep -il "$query" "$NOTES_DIR"/*.txt 2>/dev/null | sed "s|$NOTES_DIR/||g"))
                
                # If no matches, stay in the loop and ask again
                if [ ${#match_files[@]} -eq 0 ]; then
                    echo "No matches found for '$query'. Try again."
                    echo ""
                    continue
                fi
                
                # If matches are found, display them and open the sub-menu
                echo ""
                echo "--- Lines matching '$query' ---"
                grep -in --color=always "$query" "$NOTES_DIR"/*.txt | sed "s|$NOTES_DIR/||g"
                echo "-------------------------------"
                echo ""
                
                echo "Select a note from the matches to open:"
                PS3="Enter match number: "
                
                select match_opt in "${match_files[@]}" "Exit"; do
                    if [ "$match_opt" = "Exit" ]; then
                        break 3
                    elif [ -n "$match_opt" ]; then
                        gnome-text-editor "$NOTES_DIR/$match_opt" &
                        break 3
                    else
                        echo "Invalid selection."
                    fi
                done
            done
            
            # Reset the prompt variable for the main menu
            PS3="Enter a number: "
            ;;
            
        "Exit")
            echo "Exiting."
            break
            ;;
            
        *)
            if [ -n "$opt" ]; then
                gnome-text-editor "$NOTES_DIR/$opt" &
                break
            else
                echo "Invalid selection. Please try again."
            fi
            ;;
    esac
done
